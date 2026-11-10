document.addEventListener('DOMContentLoaded', () => {
    calculateBias();
});

document.getElementById('bias-form').addEventListener('submit', function(e) {
    e.preventDefault();
    calculateBias();
});

async function calculateBias() {
    // 1. ดึงค่าจากฟอร์ม
    const vcc = parseFloat(document.getElementById('vcc').value);
    const r1 = parseFloat(document.getElementById('r1').value);
    const r2 = parseFloat(document.getElementById('r2').value);
    const rc = parseFloat(document.getElementById('rc').value);
    const re = parseFloat(document.getElementById('re').value);
    const beta = parseInt(document.getElementById('beta').value);
    const vbe = parseFloat(document.getElementById('vbe').value);

    // 2. อัปเดตพารามิเตอร์วงจรพื้นฐานบนภาพ SVG
    document.getElementById('svg-vcc-label').textContent = `VCC = ${vcc.toFixed(1)} V`;
    document.getElementById('svg-r1-val').textContent = `${r1.toFixed(1)} kΩ`;
    document.getElementById('svg-r2-val').textContent = `${r2.toFixed(1)} kΩ`;
    document.getElementById('svg-rc-val').textContent = `${rc.toFixed(1)} kΩ`;
    document.getElementById('svg-re-val').textContent = `${re.toFixed(1)} kΩ`;
    document.getElementById('svg-beta-val').textContent = `(β = ${beta})`;

    try {
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vcc, r1, r2, rc, re, beta, vbe })
        });

        const data = await response.json();

        if (response.ok) {
            // 3. อัปเดตตารางผลลัพธ์ทางขวามือ
            document.getElementById('res-vb').textContent = `${data.vb_V} V`;
            document.getElementById('res-ve').textContent = `${data.ve_V} V`;
            document.getElementById('res-vc').textContent = `${data.vc_V} V`;
            document.getElementById('res-vce').textContent = `${data.vce_V} V`;
            document.getElementById('res-ib').textContent = `${data.ib_uA} µA`;
            document.getElementById('res-ic').textContent = `${data.ic_mA} mA`;
            document.getElementById('res-ie').textContent = `${data.ie_mA} mA`;

            // 4. 📍 อัปเดตตัวเลขผลลัพธ์ลงบนรูปภาพวงจร (SVG Overlays) 📍
            document.getElementById('svg-vb-val').textContent = `VB = ${data.vb_V} V`;
            document.getElementById('svg-ib-val').textContent = `IB = ${data.ib_uA} µA`;
            
            document.getElementById('svg-vc-val').textContent = `VC = ${data.vc_V} V`;
            document.getElementById('svg-ic-val').textContent = `IC = ${data.ic_mA} mA`;
            
            document.getElementById('svg-ve-val').textContent = `VE = ${data.ve_V} V`;
            document.getElementById('svg-ie-val').textContent = `IE = ${data.ie_mA} mA`;

            // 5. ปรับแสดงผล Badge สถานะ
            const statusCard = document.getElementById('status-card');
            const statusIcon = document.getElementById('status-icon');
            const badgeTitle = document.getElementById('badge-title-text');
            const badgeDesc = document.getElementById('badge-desc-text');

            statusCard.className = 'badge-status';

            if (data.status === 'Active') {
                statusCard.classList.add('badge-success');
                statusIcon.className = 'fa-solid fa-circle-check';
                badgeTitle.textContent = "Active region approximation OK";
            } else if (data.status === 'Saturation') {
                statusCard.classList.add('badge-warning');
                statusIcon.className = 'fa-solid fa-triangle-exclamation';
                badgeTitle.textContent = "Saturation region detected";
            } else {
                statusCard.classList.add('badge-danger');
                statusIcon.className = 'fa-solid fa-circle-xmark';
                badgeTitle.textContent = data.status === 'Cutoff' ? "Cutoff Region detected" : "Calculation Error";
            }
            
            badgeDesc.textContent = data.message;
        }
    } catch (err) {
        console.error(err);
    }
}