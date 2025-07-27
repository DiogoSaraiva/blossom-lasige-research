import cv2
import mediapipe as mp
import numpy as np

from mimetic.src.logging_utils import Logger

mp_drawing = mp.solutions.drawing_utils

class Visualization:
    """
    Class for visualizing face and pose landmarks, overlaying data, and drawing custom graphics on video frames.

    Attributes:
        logger (Logger): Logger instance for logging messages.
        frame (np.ndarray): Current video frame to visualize.
        mesh_results: Results from the face mesh model.
        pose_results: Results from the pose model.
        axis (dict): Dictionary containing pitch, roll, and yaw values.
        data_sent: Indicator if data has been sent.
        height (float): Estimated height value.
        fps: Frames per second value.
        blossom_data: Additional calculated data for overlay.
    """

    def __init__(self,  logger:Logger, mesh_results=None, pose_results=None):
        """
        Initializes the Visualization class with a logger, mesh results, and pose results.

        Args:
            logger (Logger): Logger instance for logging messages.
            mesh_results: Results from the face mesh model (optional).
            pose_results: Results from the pose model (optional).
        """
        self.logger = logger
        self.frame = None
        self.mesh_results = mesh_results
        self.pose_results = pose_results
        self.axis = {'pitch': 0.0, 'roll': 0.0, 'yaw': 0.0}
        self.data_sent = None
        self.height = 0.0
        self.fps = None
        self.blossom_data = None

    def update(self, frame: np.ndarray, mesh_results, pose_results, data: dict):
        """
        Updates the visualization with a new frame, mesh results, pose results, and additional data.

        Args:
            frame (np.ndarray): The current video frame to visualize.
            mesh_results: Results from the face mesh model.
            pose_results: Results from the pose model.
            data (dict): Additional data containing axis, height, fps, data_sent, and blossom_data.
        """
        self.frame = frame
        self.mesh_results = mesh_results
        self.pose_results = pose_results
        self.axis = data['axis']  # [pitch, roll, yaw]
        self.height = data['height']
        self.fps = data['fps']
        self.data_sent = data['data_sent']
        self.blossom_data = data['blossom_data']

    def draw_landmarks(self):
        """
        Draws face and pose landmarks on the current frame.

        Face landmarks are drawn in green, and pose landmarks are drawn in blue.
        """
        # Face landmarks
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
        """
        Draws a line between the left and right shoulders on the current frame.

        The line is drawn in white and visualizes shoulder alignment.
        """
        if self.pose_results.pose_landmarks:
            lm = self.pose_results.pose_landmarks[0]
            if len(lm) > 12:
                h, w = self.frame.shape[:2]
                left = lm[11]
                right = lm[12]
                x1, y1 = int(left.x * w), int(left.y * h)
                x2, y2 = int(right.x * w), int(right.y * h)
                cv2.line(self.frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

    def draw_overlay_data(self):
        """
        Draws overlay data such as pitch, roll, yaw, height, and FPS on the current frame.

        The text is displayed in green for visibility.
        """
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
        """
        Draws the calculated blossom data on the current frame.

        The data includes pitch, roll, yaw, height, and a sent status, displayed in yellow.
        """
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
        """
        Draws all overlays on the current frame.

        Calls methods to draw overlay data, blossom data, landmarks, and shoulder line.
        """
        self.draw_overlay_data()
        self.draw_blossom_data()
        #self.draw_landmarks()
        #self.draw_shoulder_line()