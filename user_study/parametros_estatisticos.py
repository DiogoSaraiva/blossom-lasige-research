import pandas as pd

df = pd.read_csv('populacao.csv')

stats_summary = {}

# Calcular estatísticas
stats_summary['tempo_frente_media'] = df['tempo_frente'].mean()
stats_summary['tempo_frente_mediana'] = df['tempo_frente'].median()
stats_summary['tempo_frente_std'] = df['tempo_frente'].std()
stats_summary['tempo_frente_moda'] = df['tempo_frente'].mode()[0]

stats_summary['tempo_lateral_media'] = df['tempo_lateral'].mean()
stats_summary['tempo_lateral_mediana'] = df['tempo_lateral'].median()
stats_summary['tempo_lateral_std'] = df['tempo_lateral'].std()
stats_summary['tempo_lateral_moda'] = df['tempo_lateral'].mode()[0]

stats_summary['switches_media'] = df['switches'].mean()
stats_summary['switches_mediana'] = df['switches'].median()
stats_summary['switches_std'] = df['switches'].std()
stats_summary['switches_moda'] = df['switches'].mode()[0]

emocao_counts = df['emocao'].value_counts()

# Abrir o ficheiro para escrever
with open('estatisticas.txt', 'w', encoding='utf-8') as f:
    f.write("=== Estatísticas descritivas ===\n")
    for k, v in stats_summary.items():
        f.write(f"{k}: {v:.2f}\n")

    f.write("\n=== Contagem das emoções ===\n")
    f.write(f"{emocao_counts.to_string()}\n")

    f.write("\n=== Conclusões automáticas ===\n")
    if stats_summary['tempo_frente_media'] > stats_summary['tempo_lateral_media']:
        f.write(f"As crianças passaram, em média, mais tempo a olhar para o robô da frente ({stats_summary['tempo_frente_media']:.1f}s) do que para o da lateral ({stats_summary['tempo_lateral_media']:.1f}s).\n")
    else:
        f.write(f"As crianças passaram, em média, mais tempo a olhar para o robô da lateral ({stats_summary['tempo_lateral_media']:.1f}s) do que para o da frente ({stats_summary['tempo_frente_media']:.1f}s).\n")

    f.write(f"O desvio padrão do tempo de observação da frente é {stats_summary['tempo_frente_std']:.1f}, indicando {'maior' if stats_summary['tempo_frente_std'] > stats_summary['tempo_lateral_std'] else 'menor'} variação em comparação com a lateral ({stats_summary['tempo_lateral_std']:.1f}).\n")

    emocao_mais_frequente = emocao_counts.idxmax()
    f.write(f"A emoção mais comum foi '{emocao_mais_frequente}' com {emocao_counts.max()} ocorrências.\n")

    f.write(f"Em média, cada criança fez cerca de {stats_summary['switches_media']:.1f} switches de direção do olhar durante os 10 minutos.\n")

    f.write("\nAnálise concluída.\n")

print("✅ Estatísticas guardadas em estatisticas.txt")
