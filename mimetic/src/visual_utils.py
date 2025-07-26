import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils

class Visualization:
    def __init__(self, frame=None, mesh_results=None, pose_results=None):
        self.frame = frame
        self.mesh_results = mesh_results
        self.pose_results = pose_results
        self.axis = {'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.data_sent = None
        self.height = 0.0
        self.fps = None
        self.blossom_data = None

    def update(self, frame, mesh_results, pose_results, data):
        self.frame = frame
        self.mesh_results = mesh_results
        self.pose_results = pose_results
        self.axis = data['axis']  # [pitch, roll, yaw]
        self.height = data['height']
        self.fps = data['fps']
        self.data_sent = data['data_sent']
        self.blossom_data = data['blossom_data']

    def draw_landmarks(self):
        if self.mesh_results.face_landmarks:
            for landmark in self.mesh_results.face_landmarks[0]:
                x = int(landmark.x * self.frame.shape[1])
                y = int(landmark.y * self.frame.shape[0])
                cv2.circle(self.frame, (x, y), 1, (0, 255, 0), -1)

        # Pose landmarks
        if self.pose_results.pose_landmarks:
            for landmark in self.pose_results.pose_landmarks[0]:
                x = int(landmark.x * self.frame.shape[1])
                y = int(landmark.y * self.frame.shape[0])
                cv2.circle(self.frame, (x, y), 2, (255, 0, 0), -1)

    def draw_shoulder_line(self):
        if self.pose_results.pose_landmarks:
            lm = self.pose_results.pose_landmarks[0]
            if len(lm) > 12:  # até aos ombros
                h, w = self.frame.shape[:2]
                left = lm[11]
                right = lm[12]
                x1, y1 = int(left.x * w), int(left.y * h)
                x2, y2 = int(right.x * w), int(right.y * h)
                cv2.line(self.frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

    def draw_overlay_data(self):
        h, w = self.frame.shape[:2]
        x_offset = 10
        y_offset = 30

        cv2.putText(self.frame,
                    f"Pitch: {self.axis['pitch']:+6.2f}  Roll: {self.axis['roll']:+6.2f}  Yaw: {self.axis['yaw']:+6.2f}",
                    (x_offset, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        y_offset += 30
        cv2.putText(self.frame,
                    f"Height: {self.height:.2f}",
                    (x_offset, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if self.fps is not None:
            fps_text = f"{self.fps:.1f} FPS"
            text_size = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            x_fps = w - text_size[0] - 10
            y_fps = 30
            cv2.putText(self.frame, fps_text, (x_fps, y_fps),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    def draw_blossom_data(self):
        h, w = self.frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        color = (0, 255, 255)
        thickness = 1
        line_height = 20

        lines = [
            f"Calculated: P={self.blossom_data['x']:.3f}, R={self.blossom_data['y']:.3f}, Y={self.blossom_data['z']:.3f}, H={self.blossom_data['h']:.3f}",
            f"Sent:      [{'X' if self.data_sent else ' '}]"
        ]

        for i, text in enumerate(lines):
            size = cv2.getTextSize(text, font, scale, thickness)[0]
            x = w - size[0] - 10
            y = h - (len(lines) - i) * line_height - 10
            cv2.putText(self.frame, text, (x, y), font, scale, color, thickness)
    def add_overlay(self):
        """Draw all overlays on the current frame."""
        self.draw_overlay_data()
        self.draw_blossom_data()
        #  self.draw_landmarks()
        # self.draw_shoulder_line()