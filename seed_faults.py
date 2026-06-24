from database import Database

db = Database()

mmi_smart_faults = [
    ("CAMERA", "REAR CAMERA NOT WORK"),
    ("CAMERA", "FRONT CAMERA NOT WORK"),
    ("CAMERA", "REAR CAMERA BLACK / BLUR"),
    ("CAMERA", "FRONT CAMERA BLACK / LINE"),
    ("CAMERA", "CAMERA SHADE / BLUR"),
    ("CAMERA", "CAMERA SPOT / BLINK"),
    ("CAMERA", "Dep -field CAM SUB"),
    ("RECEIVER", "RECEIVER NOT WORK"),
    ("RECEIVER", "RECEIVER DISTORTION"),
    ("RINGER", "SPEAKER NOT WORK"),
    ("RINGER", "SPEAKER DISTORTION"),
    ("RINGER", "AUDIO LOOP"),
    ("CAMERA", "CAMERA BLUR"),
    ("TOUCH", "TOUCH AUTO WORK"),
    ("CHARGING", "CHARGING"),
    ("LCD", "LCD BLACK"),
    ("LCD", "LCD SHADE"),
    ("LCD", "LCD SPOT / DOT"),
    ("LCD", "LCD LINE"),
    ("TOUCH", "TOUCH NOT WORK"),
    ("SENSOR", "PROXIMITY SENSOR"),
    ("SENSOR", "LIGHT GSENSOR"),
    ("SENSOR", "M/S RANG SENSOR"),
    ("OTHERS", "FINGER PRINT"),
    ("OTHERS", "BLUETOOTH"),
    ("OTHERS", "OTG"),
    ("FLASH", "FLASH LIGHT"),
    ("SENSOR", "GPS"),
    ("MEMORY CARD", "SIM / SD CARD"),
    ("AUTO OFF", "AUTO OFF"),
    ("KEYPAD", "SIDE KEY / POWER KEY"),
    ("VIBRATOR", "VIBRATOR")
]

created_by = 1  # ایڈمن یوزر آئی ڈی

# چیک کریں کہ کیٹیگری پہلے سے موجود تو نہیں
existing = db.execute_query(
    "SELECT id FROM fault_categories WHERE category_name = 'MMI Smart' AND station_type = 'MMI Test'",
    fetch_one=True
)

if existing:
    cat_id = existing['id']
    print("⚠️ 'MMI Smart' پہلے سے موجود ہے۔")
else:
    cat_id = db.add_fault_category("MMI Smart", "MMI Test", created_by=created_by, icon="📱")
    print(f"✅ 'MMI Smart' کیٹیگری بن گئی (ID: {cat_id})")

# فالٹس شامل کریں (اگر پہلے سے نہ ہوں)
for category, fault in mmi_smart_faults:
    # ہم ایک ہی کیٹیگری میں تمام فالٹس ڈال رہے ہیں، لہٰذا category کو نظر انداز کریں
    existing_fault = db.execute_query(
        "SELECT id FROM faults WHERE category_id = ? AND fault_name = ?",
        (cat_id, fault), fetch_one=True
    )
    if not existing_fault:
        db.add_fault(cat_id, fault, severity='Minor', created_by=created_by)
        print(f"   ✅ {fault} شامل")
    else:
        print(f"   ⚠️ {fault} پہلے سے موجود ہے۔")

db.close()
print("🎉 عمل مکمل! 'MMI Smart' کیٹیگری اور فالٹس شامل ہو گئے۔")