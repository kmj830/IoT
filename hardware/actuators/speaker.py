import os
import tempfile
import subprocess
import requests

def play_audio_file(audio_path_or_url):
    """
    지정된 오디오 파일 경로 또는 웹 다운로드 URL의 음성을 키트 스피커로 재생합니다.
    (리눅스/라즈베리파이: aplay/pygame, macOS: afplay 자동 지원)
    """
    temp_file = None
    target_path = audio_path_or_url

    try:
        # HTTP URL인 경우 임시 파일로 다운로드
        if audio_path_or_url.startswith("http://") or audio_path_or_url.startswith("https://"):
            print(f"📥 [Speaker] 클라우드 음성 파일 다운로드 중...")
            res = requests.get(audio_path_or_url, timeout=10)
            if res.status_code == 200:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(res.content)
                    temp_file = f.name
                    target_path = temp_file
            else:
                print(f"❌ [Speaker Error] 오디오 다운로드 실패: HTTP {res.status_code}")
                return False

        print(f"🔊 [Speaker] 음성 메시지 스피커 재생 시작: {target_path}")

        # 1. macOS 환경: 내장 afplay 명령어로 즉시 사운드 출력
        if os.uname().sysname == "Darwin":
            subprocess.run(["afplay", target_path], check=False)
            print("✅ [Speaker] 음성 재생 완료 (macOS afplay)")
            return True

        # 2. Linux / 라즈베리파이 환경: aplay 또는 pygame.mixer 사용
        try:
            subprocess.run(["aplay", target_path], check=True)
            print("✅ [Speaker] 음성 재생 완료 (Linux aplay)")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # 3. Pygame 폴백
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(target_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pass
            print("✅ [Speaker] 음성 재생 완료 (pygame.mixer)")
            return True
        except Exception as pe:
            print(f"⚠️ [Speaker Warning] 하드웨어 오디오 드라이버 부재, 음성 수신 확인만 처리: {pe}")
            return True

    except Exception as e:
        print(f"❌ [Speaker Error] 음성 재생 중 오류 발생: {e}")
        return False
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
