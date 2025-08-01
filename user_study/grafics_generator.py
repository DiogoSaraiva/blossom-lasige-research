import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuração de estilo
sns.set(style="whitegrid")

# Ler os dados
df = pd.read_csv('populacao.csv')

# 1. Gráfico de barras: distribuição das emoções
plt.figure(figsize=(8,6))
sns.countplot(x='emocao', data=df, palette='pastel')
plt.title('Distribuição das Emoções')
plt.xlabel('Emoção')
plt.ylabel('Número de Crianças')
plt.tight_layout()
#plt.savefig('grafico_barras_emocoes.png')
plt.show()

# 2. Gráfico de linhas: tempos vs ids
plt.figure(figsize=(12,6))
plt.plot(df['id'], df['tempo_frente'], label='Tempo a olhar para a frente', color='blue', marker='o')
plt.plot(df['id'], df['tempo_lateral'], label='Tempo a olhar para o lado', color='green', marker='o')
plt.title('Tempos a olhar vs Crianças')
plt.xlabel('ID da Criança')
plt.ylabel('Tempo (segundos)')
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
#plt.savefig('grafico_linhas_tempos.png')
plt.show()

# 3. Boxplot: número de switches
plt.figure(figsize=(8,6))
sns.boxplot(y='switches', data=df, palette='pastel')
plt.title('Distribuição do Número de Switches')
plt.ylabel('Número de Switches')
plt.tight_layout()
#plt.savefig('boxplot_switches.png')
plt.show()

# 4. Histograma: tempo a olhar para a frente
plt.figure(figsize=(8,6))
sns.histplot(df['tempo_frente'], bins=10, kde=True, color='skyblue')
plt.title('Distribuição do Tempo a Olhar para a Frente')
plt.xlabel('Tempo (segundos)')
plt.ylabel('Frequência')
plt.tight_layout()
#plt.savefig('histograma_tempo_frente.png')
plt.show()

print("graficos gerados com sucesso!")
