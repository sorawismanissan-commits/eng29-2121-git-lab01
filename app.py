from flask import Flask, render_template, request, jsonify

from dc_bias import calculate_divider_bias

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    
    # ดึงค่าพารามิเตอร์จาก Frontend
    vcc = float(data.get('vcc', 12))
    r1 = float(data.get('r1', 10000))    # Ohm
    r2 = float(data.get('r2', 2200))     # Ohm
    rc = float(data.get('rc', 1000))     # Ohm
    re = float(data.get('re', 470))      # Ohm
    beta = float(data.get('beta', 100))
    vbe = float(data.get('vbe', 0.7))
    
    result = calculate_divider_bias(vcc, r1, r2, rc, re, beta, vbe)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
