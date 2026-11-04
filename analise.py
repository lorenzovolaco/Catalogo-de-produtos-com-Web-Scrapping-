def processar_produtos(df_produtos, categoria_escolhida):
  
    if df_produtos is None or df_produtos.empty or not categoria_escolhida:
        return {
            'produtos': [],
            'total': 0,
            'menor_preco': None,
            'maior_preco': None,
            'preco_medio': 0,
            'melhor_avaliacao': None
        }
      

    if categoria_escolhida.strip().lower() == "all categories":
        df_filtrado = df_produtos.copy()
    else:
        df_filtrado = df_produtos[
            df_produtos['categoria'].str.strip().str.lower() == categoria_escolhida.strip().lower()
        ].copy()
    
    if df_filtrado.empty:
        return {
            'produtos': [],
            'total': 0,
            'menor_preco': None,
            'maior_preco': None,
            'preco_medio': 0,
            'melhor_avaliacao': None
        }
    
    df_filtrado = df_filtrado.astype(object).where(df_filtrado.notna(), None)

    df_com_preco = df_filtrado.dropna(subset=['preco'])
    if df_com_preco.empty:
        return {
            'produtos': df_filtrado.to_dict(orient='records'),
            'total': len(df_filtrado),
            'menor_preco': None,
            'maior_preco': None,
            'preco_medio': 0,
            'melhor_avaliacao': None
        }
      
    total = len(df_filtrado)
    
    row_menor = df_com_preco.loc[df_com_preco['preco'].idxmin()]
    menor_preco = row_menor.to_dict()
    
    row_maior = df_com_preco.loc[df_com_preco['preco'].idxmax()]
    maior_preco = row_maior.to_dict()
    
    preco_medio = round(float(df_com_preco['preco'].mean()), 2)
    
    melhor_avaliacao = None
    df_avaliacao = df_filtrado.dropna(subset=['avaliacao'])
    if not df_avaliacao.empty:
        row_avaliacao = df_avaliacao.loc[df_avaliacao['avaliacao'].idxmax()]
        melhor_avaliacao = row_avaliacao.to_dict()

    produtos_lista = df_filtrado.to_dict(orient='records')

    return {
        'produtos': produtos_lista,
        'total': total,
        'menor_preco': menor_preco,
        'maior_preco': maior_preco,
        'preco_medio': preco_medio,
        'melhor_avaliacao': melhor_avaliacao
    }
