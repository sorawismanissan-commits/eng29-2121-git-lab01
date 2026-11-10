from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def calculate_bjt_dc_bias(vcc, r1, r2, rc, re, beta, vbe=0.7):
    """
    คำนวณ DC Bias วงจร Common Emitter (Voltage Divider Bias)
    """
    try:
        # 1. คำนวณ Thevenin Equivalent Voltage (Vth) และ Resistance (Rth) ที่ขา Base
        rth = (r1 * r2) / (r1 + r2)
        vth = vcc * (r2 / (r1 + r2))
        
        # 2. คำนวณกระแสขา Base (IB)
        ib = (vth - vbe) / (rth + (1 + beta) * re)
        
        # ตรวจสอบว่าทรานซิสเตอร์นำกระแสหรือไม่
        if ib <= 0:
            return {
                "status": "Cutoff",
                "message": "ทรานซิสเตอร์อยู่ในสภาวะ Cutoff (IB <= 0)",
                "ib_uA": 0, "ic_mA": 0, "ie_mA": 0,
                "vb_V": round(vth, 2), "ve_V": 0, "vc_V": round(vcc, 2), "vce_V": round(vcc, 2)
            }
        
        # 3. คำนวณกระแส IC และ IE สภาวะ Active Region
        ic = beta * ib
        ie = (1 + beta) * ib
        
        # 4. คำนวณแรงดันตามจุดต่าง ๆ
        vb = vth - (ib * rth)
        ve = ie * re
        vc = vcc - (ic * rc)
        vce = vc - ve
        
        # 5. ตรวจสอบสภาวะการทำงาน (Operating Region)
        # คำนวณกระแสอิ่มตัว (IC_sat)
        vce_sat = 0.2  # แรงดันตกค้างสภาวะอิ่มตัวโดยประมาณ
        ic_sat = (vcc - vce_sat) / (rc + re)
        
        if vce <= vce_sat or ic >= ic_sat:
            region = "Saturation"
            ic = ic_sat
            vce = vce_sat
            vc = ve + vce_sat
            vb = ve + vbe
        else:
            region = "Active"
            
        return {
            "status": "Success",
            "region": region,
            "ib_uA": round(ib * 1e6, 2),   # แปลงเป็น uA
            "ic_mA": round(ic * 1e3, 2),   # แปลงเป็น mA
            "ie_mA": round(ie * 1e3, 2),   # แปลงเป็น mA
            "vb_V": round(vb, 2),
            "ve_V": round(ve, 2),
            "vc_V": round(vc, 2),
            "vce_V": round(vce, 2)
        }
    except Exception as e:
        return {"status": "Error", "message": str(e)}

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
    
    result = calculate_bjt_dc_bias(vcc, r1, r2, rc, re, beta, vbe)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)