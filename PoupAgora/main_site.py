from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
import mysql.connector
import openpyxl
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
import pandas as pd
from functools import wraps

app = Flask(__name__)
app.secret_key = 'chave_secreta'


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Você precisa estar logado.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="meubanco"
    )


def criar_banco():
    conn = mysql.connector.connect(host="localhost", user="root", password="")
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS meubanco;")
    cursor.execute("USE meubanco;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100),
            email VARCHAR(100),
            senha VARCHAR(100)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacoes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            descricao VARCHAR(255),
            tipo_pagamento VARCHAR(50),
            categoria VARCHAR(100),
            data DATE,
            valor DECIMAL(10,2),
            tipo VARCHAR(50),
            parcela_atual INT DEFAULT 1,
            total_parcelas INT DEFAULT 1,
            juros DECIMAL(5,2) DEFAULT 0.00,
            valor_parcela DECIMAL(10,2),
            usuario_id INT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            transacao_id INT,
            pago BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (transacao_id) REFERENCES transacoes(id) ON DELETE CASCADE
        );
    """)

    cursor.close()
    conn.close()


criar_banco()


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND senha = %s", (email, senha))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['usuario_id'] = user['id']
            return redirect(url_for('homepage'))
        else:
            flash('Email ou senha inválidos!', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('Email já cadastrado!', 'warning')
            cursor.close()
            conn.close()
            return redirect(url_for('cadastro'))

        cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)", (nome, email, senha))
        conn.commit()
        cursor.close()
        conn.close()

        flash('Cadastro realizado com sucesso!', 'success')
        return redirect(url_for('login'))

    return render_template('cadastro.html')


@app.route('/guia_teorico')
@login_required
def guia_teorico():
    return render_template('guia_teorico.html')


@app.route("/planilhas")
@login_required
def planilhas():
    usuario_id = session['usuario_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM transacoes WHERE usuario_id = %s ORDER BY data DESC", (usuario_id,))
    transacoes = cursor.fetchall()

    cursor.execute("SELECT SUM(valor) AS total_entrada FROM transacoes WHERE tipo = 'Entrada' AND usuario_id = %s", (usuario_id,))
    total_entrada = cursor.fetchone()['total_entrada'] or 0

    cursor.execute("SELECT SUM(valor) AS total_saida FROM transacoes WHERE tipo = 'Saída' AND usuario_id = %s", (usuario_id,))
    total_saida = cursor.fetchone()['total_saida'] or 0

    saldo_total = total_entrada - total_saida

    cursor.close()
    conn.close()

    df = pd.DataFrame(transacoes)
    if not df.empty:
        df['data'] = df['data'].astype(str)
        tabela_html = df.to_html(classes="table table-striped", index=False)
    else:
        tabela_html = "<p>Nenhuma transação cadastrada.</p>"

    return render_template("planilhas.html", 
                           tabela_html=tabela_html, 
                           total_entrada=total_entrada, 
                           total_saida=total_saida, 
                           saldo_total=saldo_total)


@app.route("/adicionar_transacao", methods=['POST'])
@login_required
def adicionar_transacao():
    try:
        usuario_id = session['usuario_id']
        descricao = request.form['descricao']
        tipo_pagamento = request.form['tipo_pagamento']
        categoria = request.form['categoria']
        data = request.form['data']
        valor_total = float(request.form['valor'])
        tipo = request.form['tipo']
        parcelas = int(request.form.get('parcelas', 1))
        juros = float(request.form.get('juros', 0.0))

        conn = get_db_connection()
        cursor = conn.cursor()

        if tipo_pagamento == "cartao" and parcelas > 1:
            if juros > 0:
                j = juros / 100
                valor_parcela = valor_total * (j * (1 + j)**parcelas) / ((1 + j)**parcelas - 1)
            else:
                valor_parcela = valor_total / parcelas
            for i in range(parcelas):
                data_parcela = datetime.strptime(data, "%Y-%m-%d") + timedelta(days=30 * i)
                cursor.execute("""
                    INSERT INTO transacoes (descricao, tipo_pagamento, categoria, data, valor, tipo, parcela_atual, total_parcelas, juros, valor_parcela, usuario_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (descricao, tipo_pagamento, categoria, data_parcela, valor_parcela, tipo, i+1, parcelas, juros, valor_parcela, usuario_id))
        else:
            cursor.execute("""
                INSERT INTO transacoes (descricao, tipo_pagamento, categoria, data, valor, tipo, usuario_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (descricao, tipo_pagamento, categoria, data, valor_total, tipo, usuario_id))

        conn.commit()
        cursor.close()
        conn.close()

        create_bar_chart(usuario_id)
        create_pie_chart_week(usuario_id)
        create_pie_chart_month(usuario_id)

        flash('Transação salva com sucesso!', 'success')
    except Exception as e:
        print(f"Erro: {e}")
        flash('Erro ao salvar a transação.', 'danger')

    return redirect(url_for('planilhas'))


@app.route("/pagar_parcela/<int:transacao_id>", methods=["POST"])
@login_required
def pagar_parcela(transacao_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pagamentos (transacao_id, pago)
            VALUES (%s, 1)
            ON DUPLICATE KEY UPDATE pago = 1
        """, (transacao_id,))
        conn.commit()
        flash("Parcela paga com sucesso!", "success")
    except Exception as e:
        print(f"Erro: {e}")
        flash("Erro ao pagar parcela.", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("homepage"))


@app.route("/homepage")
@login_required
def homepage():
    usuario_id = session['usuario_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, descricao, data, valor, tipo, parcela_atual, total_parcelas 
        FROM transacoes 
        WHERE usuario_id = %s AND 
              (parcela_atual = 1 OR (parcela_atual > 1 AND DATE_ADD(data, INTERVAL (parcela_atual - 1) MONTH) <= CURDATE()))
          AND (tipo_pagamento != 'cartao' OR id NOT IN (SELECT transacao_id FROM pagamentos WHERE pago = 1))
          AND tipo != 'Entrada'
        ORDER BY data ASC
    """, (usuario_id,))
    transacoes = cursor.fetchall()

    cursor.execute("SELECT SUM(valor) AS total_entrada FROM transacoes WHERE tipo = 'Entrada' AND usuario_id = %s", (usuario_id,))
    total_entrada = cursor.fetchone()['total_entrada'] or 0

    cursor.execute("SELECT SUM(valor) AS total_saida FROM transacoes WHERE tipo = 'Saída' AND usuario_id = %s", (usuario_id,))
    total_saida = cursor.fetchone()['total_saida'] or 0

    saldo_total = total_entrada - total_saida

    cursor.close()
    conn.close()

    return render_template("homepage.html", transacoes=transacoes, total_entrada=total_entrada, total_saida=total_saida, saldo_total=saldo_total)

@app.route("/evento/<int:dia>")
def evento(dia):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM transacoes WHERE id = %s", (dia,))
    transacao = cursor.fetchone()

    conn.close()

    if not transacao:
        return render_template("evento.html", evento="Nenhuma transação encontrada.")

    return render_template("evento.html", evento=transacao)

def create_bar_chart(usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday() + 1)
    fim_semana = inicio_semana + timedelta(days=6)

    diagasto = [0] * 7  
    diarecebido = [0] * 7  

    cursor.execute("""
        SELECT DAYOFWEEK(data) AS dia_semana, tipo, SUM(valor) AS total
        FROM transacoes
        WHERE data BETWEEN %s AND %s AND usuario_id = %s
        GROUP BY dia_semana, tipo
    """, (inicio_semana, fim_semana, usuario_id))

    resultados = cursor.fetchall()
    for resultado in resultados:
        dia_semana = resultado['dia_semana'] - 1
        if resultado['tipo'] == 'Saída':
            diagasto[dia_semana] = float(resultado['total'])
        elif resultado['tipo'] == 'Entrada':
            diarecebido[dia_semana] = float(resultado['total'])

    cursor.close()
    conn.close()

    semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
    posição_a = list(range(len(semana)))
    posição_b = [pos + 0.4 for pos in posição_a]

    plt.figure(figsize=(8, 4))
    plt.bar(posição_a, diagasto, width=0.4, color='#5c6b4b', label="Saída")
    plt.bar(posição_b, diarecebido, width=0.4, color='#3d4831', label="Entrada")
    plt.title("Gastos e Recebimentos Semanais", fontsize=14)
    plt.ylabel("Valores", fontsize=12)
    plt.xticks(ticks=[pos + 0.2 for pos in posição_a], labels=semana)
    plt.legend(title="Legenda", loc="upper left", fontsize=10)
    plt.tight_layout()

    GRAPH_FOLDER = os.path.join(os.getcwd(), "static", "graphs")
    os.makedirs(GRAPH_FOLDER, exist_ok=True)
    chart_path = os.path.join(GRAPH_FOLDER, "bar_chart.png")
    plt.savefig(chart_path)
    plt.close()

def create_pie_chart_week(usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday() + 1)
    fim_semana = inicio_semana + timedelta(days=6)

    cursor.execute("""
        SELECT tipo, SUM(valor) AS total
        FROM transacoes
        WHERE data BETWEEN %s AND %s AND usuario_id = %s
        GROUP BY tipo
    """, (inicio_semana, fim_semana, usuario_id))

    resultados = cursor.fetchall()
    gastos_semana = 0
    recebimentos_semana = 0

    for resultado in resultados:
        total = resultado['total'] or 0
        if resultado['tipo'] == 'Saída':
            gastos_semana = float(total)
        elif resultado['tipo'] == 'Entrada':
            recebimentos_semana = float(total)

    cursor.close()
    conn.close()

    labels_week = ['Gastos da Semana', 'Ganhos da Semana']
    sizes_week = [gastos_semana, recebimentos_semana]
    colors_week = ['#5c6b4b', '#3d4831']

    plt.figure(figsize=(4, 4))
    plt.pie(
        sizes_week,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors_week,
        wedgeprops={'width': 0.4}
    )
    plt.title("Gastos e Ganhos Semanais", fontsize=14)
    plt.legend(labels_week, loc="upper right", fontsize=10)
    plt.axis('equal')

    GRAPH_FOLDER = os.path.join(os.getcwd(), "static", "graphs")
    os.makedirs(GRAPH_FOLDER, exist_ok=True)
    chart_path = os.path.join(GRAPH_FOLDER, "pie_chart_week.png")
    plt.savefig(chart_path)
    plt.close()

def create_pie_chart_month(usuario_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    hoje = datetime.now().date()
    mes_atual = hoje.month
    ano_atual = hoje.year

    cursor.execute("""
        SELECT tipo, SUM(valor) AS total
        FROM transacoes
        WHERE MONTH(data) = %s AND YEAR(data) = %s AND usuario_id = %s
        GROUP BY tipo
    """, (mes_atual, ano_atual, usuario_id))

    resultados = cursor.fetchall()
    gastos_mes = 0
    recebimentos_mes = 0

    for resultado in resultados:
        total = resultado['total'] or 0
        if resultado['tipo'] == 'Saída':
            gastos_mes = float(total)
        elif resultado['tipo'] == 'Entrada':
            recebimentos_mes = float(total)

    cursor.close()
    conn.close()

    labels_month = ['Gastos do Mês', 'Ganhos do Mês']
    sizes_month = [gastos_mes, recebimentos_mes]
    colors_month = ['#5c6b4b', '#3d4831']

    plt.figure(figsize=(4, 4))
    plt.pie(
        sizes_month,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors_month,
        wedgeprops={'width': 0.4}
    )
    plt.title("Gastos e Ganhos Mensais", fontsize=14)
    plt.legend(labels_month, loc="upper right", fontsize=10)
    plt.axis('equal')

    GRAPH_FOLDER = os.path.join(os.getcwd(), "static", "graphs")
    os.makedirs(GRAPH_FOLDER, exist_ok=True)
    chart_path = os.path.join(GRAPH_FOLDER, "pie_chart_month.png")
    plt.savefig(chart_path)
    plt.close()


if __name__ == "__main__":
    app.run(debug=True)