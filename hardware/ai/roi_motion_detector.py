import time
import random

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    OPENCV_AVAILABLE = False


class DoorwayRoiMotionDetector:
    """
    현관문 관심 구역(ROI) 반려견 배회 및 장시간 체류 감지기
    - 논문 근거: Ogata (2016) - 분리불안견의 핵심 징후인 출입구(현관) 서성임 및 집중 응시 포착
    - RPi 3B 최적화: 전체 화면이 아닌 현관문 영역만 크롭하여 프레임 차분/MOG2 연산 (CPU 부하 최소화)
    """
    def __init__(self, roi_box=(0.1, 0.3, 0.5, 0.95), stay_threshold_sec=5.0):
        """
        :param roi_box: (x_min, y_min, x_max, y_max) 정규화된 현관문 사각 영역 (0.0~1.0)
        :param stay_threshold_sec: 현관 영역 내 지속 체류 시 이상행동으로 판정할 기준 초
        """
        self.roi_box = roi_box
        self.stay_threshold_sec = stay_threshold_sec
        self.pacing_start_time = None
        self.prev_roi_gray = None
        self.subtractor = None
        if OPENCV_AVAILABLE:
            try:
                self.subtractor = cv2.createBackgroundSubtractorMOG2(history=30, varThreshold=25, detectShadows=False)
            except Exception:
                pass

    def process_frame(self, frame):
        """
        카메라 프레임을 분석하여 현관문 ROI 내 반려견 배회 여부를 판별합니다.
        :return: (is_pacing_alert, duration_sec, motion_ratio)
        """
        if not OPENCV_AVAILABLE or frame is None or self.subtractor is None:
            return False, 0.0, 0.0

        h, w = frame.shape[:2]
        x1 = int(self.roi_box[0] * w)
        y1 = int(self.roi_box[1] * h)
        x2 = int(self.roi_box[2] * w)
        y2 = int(self.roi_box[3] * h)

        # 1. 현관문 영역(ROI) 크롭
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False, 0.0, 0.0

        # 2. 배경 차분으로 움직임 마스크 생성
        fg_mask = self.subtractor.apply(roi)
        motion_pixels = cv2.countNonZero(fg_mask)
        roi_total_pixels = (x2 - x1) * (y2 - y1)
        motion_ratio = motion_pixels / float(roi_total_pixels) if roi_total_pixels > 0 else 0

        now = time.time()
        # 현관 영역 내 유의미한 움직임(5% 이상 픽셀 변화) 발생 확인
        if motion_ratio >= 0.05:
            if self.pacing_start_time is None:
                self.pacing_start_time = now
            duration = now - self.pacing_start_time
            if duration >= self.stay_threshold_sec:
                return True, round(duration, 1), round(motion_ratio, 2)
        else:
            # 움직임이 멈추거나 벗어남
            self.pacing_start_time = None

        return False, 0.0, round(motion_ratio, 2)

    def simulate_pacing_detection(self):
        """개발/시뮬레이션 환경용 현관문 배회 감지 시뮬레이터"""
        sim_duration = round(random.uniform(5.5, 9.8), 1)
        sim_ratio = round(random.uniform(0.12, 0.35), 2)
        return True, sim_duration, sim_ratio


_roi_detector = DoorwayRoiMotionDetector()

def check_doorway_pacing(frame=None, simulate=False):
    """
    현관문 배회 감지 편의 함수
    """
    if simulate or not OPENCV_AVAILABLE or frame is None:
        return _roi_detector.simulate_pacing_detection()
    return _roi_detector.process_frame(frame)
