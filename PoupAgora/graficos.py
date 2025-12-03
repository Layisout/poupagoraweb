#Grafico de barras verticais
import matplotlib.pyplot as plt

# Dados
diagasto = [100, 10, 100, 100, 100, 10, 100]
diarecebido = [10, 100, 10, 10, 10, 100, 10]
semana = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

# Configuração das posições das barras
posição_a = list(range(len(semana)))
posição_b = [pos + 0.4 for pos in posição_a]  # Alinhamento entre barras

# Tamanho e estilo do gráfico
plt.figure(figsize=(8, 4))  # Dimensão horizontal
plt.bar(posição_a, diagasto, width=0.4, color='#5c6b4b', label="Gasto")  # Azul claro
plt.bar(posição_b, diarecebido, width=0.4, color='#3d4831', label="Recebido")  # Azul escuro

# Adicionando rótulos e legendas
plt.title("Gastos e Recebimentos Semanais", fontsize=14)
plt.ylabel("Valores", fontsize=12)
plt.xticks(ticks=[pos + 0.2 for pos in posição_a], labels=semana)  # Centraliza os rótulos dos dias
plt.legend(title="Legenda", loc="upper left", fontsize=10)

# Ajuste do layout para evitar cortes
plt.tight_layout()

# Exibição do gráfico
plt.show()

#Grafico de pizza 
import matplotlib.pyplot as plt

# Primeiro gráfico de pizza
labels_week = ['Gastos da Semana', 'Ganhos da Semana']
sizes_week = [40, 30]
colors_week = ['#5c6b4b', '#3d4831']  # Cores consistentes com o gráfico de barras

fig1, ax1 = plt.subplots()
ax1.pie(
    sizes_week, 
    labels=labels_week, 
    autopct='%1.1f%%', 
    startangle=90, 
    colors=colors_week, 
    wedgeprops={'width': 0.4}  # Cria o efeito de anel
)
ax1.axis('equal')  # Mantém o gráfico circular
plt.title("Gastos e Ganhos Semanais", fontsize=14)

# Exibe o primeiro gráfico
plt.show()

# Segundo gráfico de pizza
labels_month = ['Gastos do Mês', 'Ganhos do Mês']
sizes_month = [40, 60]
colors_month = ['#5c6b4b', '#3d4831']  # Cores para diferenciar o gráfico mensal

fig2, ax2 = plt.subplots()
ax2.pie(
    sizes_month, 
    labels=labels_month, 
    autopct='%1.1f%%', 
    startangle=90, 
    colors=colors_month, 
    wedgeprops={'width': 0.4}  # Cria o efeito de anel
)
ax2.axis('equal')  # Mantém o gráfico circular
plt.title("Gastos e Ganhos Mensais", fontsize=14)

# Exibe o segundo gráfico
plt.show()