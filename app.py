from flask import Flask, render_template, request
from webscraping import coletar_produtos
from analise import processar_produtos

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/pesquisar', methods=['POST'])
def pesquisar():
    categoria_escolhida = request.form.get('categoria')
    
    try:
        df_produtos = coletar_produtos()
    except Exception as e:
        df_produtos = None
        print(f"Erro ao executar o Web Scraping: {e}")
  
    resultado = processar_produtos(df_produtos, categoria_escolhida)
  
    return render_template(
        'resultado.html',
        categoria=categoria_escolhida,
        dados=resultado
    )

if __name__ == '__main__':
    app.run(debug=True)
