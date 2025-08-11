import csv
import random

num_people = 30
ids = [f'C{str(i).zfill(2)}' for i in range(1, num_people + 1)]
possible_emotions = ['happy', 'confused', 'neutral']

with open('population.csv', mode='w', newline='') as file:
    writer = csv.writer(file)

    # Header row
    writer.writerow(['id', 'time_forward', 'time_side', 'switches', 'emotion'])

    for person_id in ids:
        # Generate random times that sum to 600
        time_forward = random.randint(100, 500)  # time between 100s and 500s
        time_side = 600 - time_forward

        # Number of switches between 2 and 20
        switches = random.randint(2, 20)

        emotion = random.choice(possible_emotions)

        writer.writerow([person_id, time_forward, time_side, switches, emotion])

print("CSV successfully created: population.csv")
