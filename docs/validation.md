# Browser Acceptance Validation (A1–A5)

**ค่าพารามิเตอร์พื้นฐานที่ใช้ร่วมกันใน A1–A5:**
- $V_{CC} = 12\text{ V}$
- $R_C = 2.2\text{ k}\Omega$
- $\beta = 100$
- $V_{BE} = 0.70\text{ V}$
- **เกณฑ์การยอมรับ:** ผลต่างไม่เกิน $0.01\text{ mA}$ สำหรับ $I_C$ และ $0.02\text{ V}$ สำหรับ $V_{CE}$

| กรณี | เลือกโหมดและกรอกค่า | คาดหมายก่อนรัน | เห็นจริง | วิธีตรวจ | สถานะ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A1 · โหมดเดิม** | Divider · $R_1 = 100\text{ k}\Omega, R_2 = 22\text{ k}\Omega, R_E = 1\text{ k}\Omega$ | ผลต้องตรงกับเมื่อรัน Lab 2 ก่อนแก้ และเทียบได้กับค่าอ้างอิงเดิม<br>$I_C = 1.23\text{ mA} \cdot V_{CE} = 8.05\text{ V}$ | **$I_C$ = 1.23 mA · $V_{CE}$ = 8.05 V**<br>$V_B$ 1.94 V · $V_E$ 1.24 V · $V_C$ 9.29 V · $I_B$ 12.3 µA · $I_E$ 1.24 mA | OpenCode Browser: เปิด `?mode=divider` → กรอกค่า → กด Calculate → อ่านตารางหลังโหลด (HTTP 200) | **PASS** |
| **A2 · Fixed** | Fixed · $R_B = 1\text{ M}\Omega$ | คำนวณได้โดยไม่ต้องกรอก $R_E$<br>$I_C = 1.13\text{ mA} \cdot V_{CE} = 9.51\text{ V}$ | **$I_C$ = 1.13 mA · $V_{CE}$ = 9.51 V**<br>$V_B$ 0.70 V · $V_E$ 0.00 V · $V_C$ 9.51 V · $I_B$ 11.3 µA · $I_E$ 1.14 mA | OpenCode Browser: เปิด `?mode=fixed` (ฟอร์มไม่มีช่อง $R_E$) → กรอก $R_B$ 1 MΩ → Calculate (HTTP 200) | **PASS** |
| **A3 · Emitter** | Emitter · $R_B = 1\text{ M}\Omega, R_E = 1\text{ k}\Omega$ | มีช่องและใช้ค่า $R_E$<br>$I_C = 1.03\text{ mA} \cdot V_{CE} = 8.71\text{ V}$ | **$I_C$ = 1.03 mA · $V_{CE}$ = 8.71 V**<br>$V_B$ 1.74 V · $V_E$ 1.04 V · $V_C$ 9.74 V · $I_B$ 10.3 µA · $I_E$ 1.04 mA | OpenCode Browser: เปิด `?mode=emitter` → กรอก $R_B$ 1 MΩ, $R_E$ 1 kΩ → Calculate (HTTP 200) | **PASS** |
| **A4 · เปลี่ยนค่าเดียว** | Emitter · เหมือน A3 แต่เปลี่ยน $R_E$ เป็น $2\text{ k}\Omega$ | ทำนายก่อนรันว่า $I_C$ จะลดลงจาก A3 (เหลือประมาณ $0.94\text{ mA}$) เพราะความต้านทาน $R_E$ ที่เพิ่มขึ้นทำให้ตัวหารในสมการ $I_B$ มากขึ้น กระแสเบสและคอลเลกเตอร์จึงลดลง แล้วบันทึกผลจริง | **$I_C$ = 0.94 mA** (ลดจาก A3 0.09 mA) · **$V_{CE}$ = 8.03 V**<br>$V_B$ 2.60 V · $V_E$ 1.90 V · $V_C$ 9.93 V · $I_B$ 9.4 µA · $I_E$ 0.95 mA | OpenCode Browser: คงค่าเหมือน A3 เปลี่ยนเฉพาะ $R_E$ = 2 kΩ → Calculate (HTTP 200) | **PASS** |
| **A5 · อินพุตผิด** | Fixed · $R_B = 0$ | มีข้อความให้แก้ $R_B$ (ต้องมากกว่า 0) เว็บไม่ล่ม และไม่แสดงผลเดิมเป็นผลของรอบนี้ (และมีการตรวจอินพุตใน Flask ด้วย) | **HTTP 400** · badge แดง "Calculation Error — Fixed Bias"<br>ข้อความ "RB ต้องมากกว่า 0" · ตารางผลเป็น — ทั้ง 7 ช่อง | OpenCode Browser: เปิด `?mode=fixed` ใส่ $R_B$ = 0 → Calculate → ตรวจ badge, ตาราง และ HTTP status | **PASS** |

หมายเหตุ: รันผ่าน OpenCode Browser tool (Chrome จริง) — Playwright MCP ยังไม่ติดตั้งในเครื่องนี้; ค่าคาดหมายอ้างอิงจากตารางใบงานเท่านั้น
