from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # 라즈베리파이 및 외부 접속을 위해 host='0.0.0.0' 설정
    app.run(host='0.0.0.0', port=5000, debug=True)
