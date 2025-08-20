import csv
import random

num_people = 30
ids = [f'C{str(i).zfill(2)}' for i in range(1, num_people + 1)]
possible_emotions = ['happy', 'confused', 'neutral', 'calm', 'sad', 'angry', 'surprised']

with open('population.csv', mode='w', newline='') as file:
    writer = csv.writer(file)

    # Header row
    writer.writerow(['id', 'time_mimic', 'time_dancer', 'switches', 'emotion_before', 'emotion_after', 'dancing_time', 'distraction_scale'])

    for person_id in ids:
        # Generate random times that sum to 600
        time_mimic = random.randint(100, 500)  # time between 100s and 500s
        time_dancer= 600 - time_mimic

        # Number of switches between 2 and 20
        switches = random.randint(2, 20)
        distraction_scale = random.randint(1, 5)

        emotion_before = random.choice(possible_emotions)
        emotion_after = random.choice(possible_emotions)

        dancing_time = round(random.uniform(0, 90), 1)
        dancing_time_str = f"{dancing_time}%"

        writer.writerow([person_id, time_mimic, time_dancer, switches, emotion_before, emotion_after, dancing_time_str, distraction_scale])

print("CSV successfully created: population.csv")
