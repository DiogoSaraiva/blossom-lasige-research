import cv2
import mediapipe as mp
import numpy as np

from mimetic.src.logging_utils import Logger

mp_drawing = mp.solutions.drawing_utils

class Visualization:
    def __init__(self, frame: np.ndarray=None, mesh_results=None, pose_results=None, logger: Logger=None):
        """
        Initializes the Visualization class with a frame, mesh results, pose results, and a logger.
        :param frame: The current video frame to visualize.
        :type frame: np.ndarray
        :param mesh_results: Results from the face mesh model.
        :type mesh_results: mediapipe.framework.formats.landmark_pb2.NormalizedLand
        """
        self.logger = logger
        self.frame = frame
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
        :param frame: The current video frame to visualize.
        :type frame: np.ndarray
        :param mesh_results: Results from the face mesh model.
        :type mesh_results: mediapipe.framework.formats.landmark_pb2.NormalizedLand
        :param pose_results: Results from the pose model.
        :type pose_results: mediapipe.framework.formats.landmark_pb2.NormalizedLand
        :param data: Additional data containing axis, height, fps, data_sent, and blossom
        :type data: dict
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
        This method draws circles on the frame for each landmark detected in the face mesh and pose results.
        It uses the coordinates of the landmarks to position the circles on the frame.
        The face landmarks are drawn in green and the pose landmarks in blue.
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
        This method checks if the pose landmarks are available and draws a line connecting the left and right
        shoulders. The line is drawn in white and is useful for visualizing the shoulder alignment.
        It uses the coordinates of the left and right shoulder landmarks to determine the endpoints of the line.
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
        This method displays the current pitch, roll, yaw, and height values on the frame.
        It uses OpenCV's putText function to render the text on the frame at specified offsets.
        The text is displayed in green color and uses a specific font size and thickness for visibility.
        The FPS (frames per second) is also displayed if available, positioned at the top right corner of the frame.
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
        This method displays the calculated values for pitch, roll, yaw, and height in a formatted string.
        It uses OpenCV's putText function to render the text on the frame at specified offsets.
        The text is displayed in yellow color and uses a specific font size and thickness for visibility.
        Additionally, it indicates whether the data has been sent with a simple checkbox-like representation.
        The text is positioned at the bottom right corner of the frame, with a line height for
        clear separation between multiple lines of text.
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
        Draw all overlays on the current frame.
        This method calls other methods to draw the overlay data, blossom data, landmarks, and shoulder line.
        """
        self.draw_overlay_data()
        self.draw_blossom_data()
        #  self.draw_landmarks()
        # self.draw_shoulder_line()