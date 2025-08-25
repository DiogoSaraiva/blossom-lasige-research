import os

import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns

# LOG_FOLDER = "output"
log_file : str = ""

#for log in LOG_FOLDER:
 #   log_file = os.path.join(log, "log.json")

records = []
with open(log_file, 'r') as f:
    for line in f:
        record = json.loads(line)

        flat_record = {
            'timestamp': pd.to_datetime(record['timestamp']),
            'data_sent': record['data']['data_sent'],
            'pitch': record['data']['axis']['pitch'],
            'roll': record['data']['axis']['roll'],
            'yaw': record['data']['axis']['yaw'],
            'blossom_x': record['data']['blossom_data']['x'],
            'blossom_y': record['data']['blossom_data']['y'],
            'blossom_z': record['data']['blossom_data']['z'],
            'blossom_h': record['data']['blossom_data']['h'],
            'blossom_e': record['data']['blossom_data']['e'],
            'height': record['data']['height'],
            'gaze_label': record['data']['gaze']['label'],
            'gaze_ratio': record['data']['gaze']['ratio'],
            'fps': record['data']['fps']
        }
        records.append(flat_record)

df = pd.DataFrame(records)

print(df.describe())

plt.figure(figsize=(12,6))
plt.plot(df['timestamp'], df['pitch'], label='Pitch')
plt.plot(df['timestamp'], df['roll'], label='Roll')
plt.plot(df['timestamp'], df['yaw'], label='Yaw')
plt.xlabel('Timestamp')
plt.ylabel('Angle')
plt.title('Pitch, Roll and Yaw')
plt.legend()
plt.show()

sns.countplot(x='gaze_label', data=df)
plt.title('Gaze Distribution')
plt.show()

plt.figure(figsize=(10,8))
sns.heatmap(df.corr(), annot=True, fmt=".2f")
plt.title('Matriz de Correlação')
plt.show()

plt.figure(figsize=(12,6))
plt.plot(df['timestamp'], df['fps'], label='FPS')
plt.xlabel('Timestamp')
plt.ylabel('FPS')
plt.title('FPS')
plt.show()
