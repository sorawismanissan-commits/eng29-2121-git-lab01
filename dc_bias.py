"""การคำนวณ DC Bias ของ BJT: Fixed Bias, Emitter Bias และ Voltage Divider Bias

ทุกฟังก์ชันรับค่าเป็นหน่วย SI (V, Ω) และคืนพจนานุกรมด้วยคีย์/หน่วยชุดเดียวกัน:
    status, region, message, ib_uA, ic_mA, ie_mA, vb_V, ve_V, vc_V, vce_V

สมการอ้างอิงใบงาน Lab 2 (Engineering Electronics)
    Fixed:   IB = (VCC - VBE) / RB
    Emitter: IB = (VCC - VBE) / (RB + (1 + β)·RE)
    Divider: RTH = R1·R2 / (R1 + R2), VTH = VCC·R2 / (R1 + R2)
             IB = (VTH - VBE) / (RTH + (1 + β)·RE)
    IC = β·IB, IE = (1 + β)·IB, VB = VE + VBE, VC = VCC - IC·RC, VCE = VC - VE
"""

VCE_SAT = 0.2  # แรงดันตกค้างสภาวะอิ่มตัวโดยประมาณ (V)

_CUTOFF_MESSAGE = "IB ≤ 0: อยู่ใน Cutoff (แบบจำลอง active region ใช้ไม่ได้)"


def _pack(region, message, ib, ic, ie, vb, ve, vc, vce):
    """แปลงหน่วย SI (A, V) เป็น µA/mA/V แล้วปัดทศนิยม 4 ตำแหน่ง"""
    return {
        "status": "Success",
        "region": region,
        "message": message,
        "ib_uA": round(ib * 1e6, 4),
        "ic_mA": round(ic * 1e3, 4),
        "ie_mA": round(ie * 1e3, 4),
        "vb_V": round(vb, 4),
        "ve_V": round(ve, 4),
        "vc_V": round(vc, 4),
        "vce_V": round(vce, 4),
    }


def _cutoff(vcc, vb):
    return _pack("Cutoff", _CUTOFF_MESSAGE, 0.0, 0.0, 0.0, vb, 0.0, vcc, vcc)


def _solve_region(vcc, rc, re, beta, ib, vbe):
    """แก้กระแส/แรงดันและจำแนก Active | Saturation (คงวิธี clamp เดิมของ Divider)"""
    ic = beta * ib
    ie = (1 + beta) * ib
    ve = ie * re
    vb = ve + vbe
    vc = vcc - (ic * rc)
    vce = vc - ve

    ic_sat = (vcc - VCE_SAT) / (rc + re)

    if vce <= VCE_SAT or ic >= ic_sat:
        # คงพฤติกรรมเดิม: clamp กระแสอิ่มตัวและ VCE ที่ 0.2 V
        ic = ic_sat
        vce = VCE_SAT
        vc = ve + VCE_SAT
        vb = ve + vbe
        message = (
            f"VCE {vce:.2f} V < {VCE_SAT:.2f} V: Saturation "
            "(การประมาณ active region ใช้ไม่ได้)"
        )
        return _pack("Saturation", message, ib, ic, ie, vb, ve, vc, vce)

    message = f"VCE = {vce:.2f} V > {VCE_SAT:.2f} V (transistor in active region)"
    return _pack("Active", message, ib, ic, ie, vb, ve, vc, vce)


def calculate_fixed_bias(vcc, rb, rc, beta, vbe=0.7):
    """Fixed Bias: IB = (VCC - VBE) / RB, ไม่มี RE (VE = 0)"""
    ib = (vcc - vbe) / rb
    if ib <= 0:
        return _cutoff(vcc, vcc)
    return _solve_region(vcc, rc, 0.0, beta, ib, vbe)


def calculate_emitter_bias(vcc, rb, re, rc, beta, vbe=0.7):
    """Emitter Bias: IB = (VCC - VBE) / (RB + (1 + β)·RE)"""
    ib = (vcc - vbe) / (rb + (1 + beta) * re)
    if ib <= 0:
        return _cutoff(vcc, vcc)
    return _solve_region(vcc, rc, re, beta, ib, vbe)


def calculate_divider_bias(vcc, r1, r2, rc, re, beta, vbe=0.7):
    """Voltage Divider Bias: คงสมการเดิมของ Lab 2"""
    rth = (r1 * r2) / (r1 + r2)
    vth = vcc * (r2 / (r1 + r2))

    ib = (vth - vbe) / (rth + (1 + beta) * re)
    if ib <= 0:
        return _cutoff(vcc, vth)
    return _solve_region(vcc, rc, re, beta, ib, vbe)
