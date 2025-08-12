import csv
import random


num_pessoas = 30
ids = [f'C{str(i).zfill(2)}' for i in range(1, num_pessoas+1)]
emocoes_possiveis = ['alegria', 'confusa', 'neutra']

with open('populacao.csv', mode='w', newline='') as file:
    writer = csv.writer(file)

    # Coluna
    writer.writerow(['id', 'tempo_frente', 'tempo_lateral', 'switches', 'emocao'])

    for person_id in ids:
        # Gerar tempos aleatórios que somam 600
        tempo_frente = random.randint(100, 500)  # tempo entre 100s e 500s
        tempo_lateral = 600 - tempo_frente

        # Número de switches entre 2 e 20
        switches = random.randint(2, 20)

        emocao = random.choice(emocoes_possiveis)

        writer.writerow([person_id, tempo_frente, tempo_lateral, switches, emocao])

print("CSV criado com sucesso: populacao.csv")
