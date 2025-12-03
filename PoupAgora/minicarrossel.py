from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    itens = ["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]
    return render_template("index.html", itens=itens)

if __name__ == "__main__":
    app.run(debug=True)