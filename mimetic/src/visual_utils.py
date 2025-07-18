import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
TESSELATION = mp_face_mesh.FACEMESH_TESSELATION

class Visualization:
    def __init__(self, frame, mesh_results, pose_results, info):
        self.frame = frame
        self.mesh_results = mesh_results
        self.pose_results = pose_results
        self.axis = info['axis']  # [pitch, roll, yaw]
        self.height = info['height']
        self.fps = info['fps']
        blossom_data = info['blossom_data']
        self.calc_data = blossom_data['calc_data']
        self.sent_data = blossom_data['sent_data']

    def draw_landmarks(self):
        if self.mesh_results.multi_face_landmarks:
            mp_drawing.draw_landmarks(
                self.frame,
                self.mesh_results.multi_face_landmarks[0],
                TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
            )

    def draw_shoulder_line(self):
        if self.pose_results.pose_landmarks:
            h, w = self.frame.shape[:2]
            lm = self.pose_results.pose_landmarks.landmark
            left = lm[mp_pose.PoseLandmark.LEFT_SHOULDER]
            right = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]
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

    def draw_sent_data(self):
        h, w = self.frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        color = (0, 255, 255)
        thickness = 1
        line_height = 20

        lines = [
            f"Calculated: P={self.calc_data['x']:.3f}, R={self.calc_data['y']:.3f}, Y={self.calc_data['z']:.3f}, H={self.calc_data['h']:.3f}",
            f"Sent:       P={self.sent_data['x']:.3f}, R={self.sent_data['y']:.3f}, Y={self.sent_data['z']:.3f}, H={self.sent_data['h']:.3f}"
        ]

        for i, text in enumerate(lines):
            size = cv2.getTextSize(text, font, scale, thickness)[0]
            x = w - size[0] - 10
            y = h - (len(lines) - i) * line_height - 10
            cv2.putText(self.frame, text, (x, y), font, scale, color, thickness)
