import os
import qrcode

students = [
    {
        "name": "mohamed-alaa-eldeen-mahmoud",
        "codes": ["fa0082", "fa0083", "fa0084"],
    },
    {
        "name": "ahmed-zakaria-abdelgalil-mohamed",
        "codes": ["fa0085", "fa0086", "fa0087"],
    },
    {
        "name": "karim-abbas-abdelfattah-abdelghany",
        "codes": ["fa0088", "fa0089", "fa0090"],
    },
    {
        "name": "ahmed-mohamed-thabet-younes",
        "codes": ["fa0091", "fa0092", "fa0093"],
    },
    {
        "name": "shaaban-ahmed-hemida",
        "codes": ["fa0094", "fa0095", "fa0096"],
    },
    {
        "name": "yasser-atef-seleem",
        "codes": ["fa0097", "fa0098", "fa0099"],
    },
    {
        "name": "youssef-mohamed-sobhy-ali",
        "codes": ["fa0100", "fa0101", "fa0102"],
    },
    {
        "name": "mahmoud-emam-ali-hassan",
        "codes": ["fa0103", "fa0104", "fa0105"],
    },
    {
        "name": "hamed-ragab-hamed-mohamed",
        "codes": ["fa0106", "fa0107", "fa0108"],
    },
]

BASE_URL = "https://www.futureacademey.com/certificate"

# Create main certificate folder
os.makedirs("certificate", exist_ok=True)


for student in students:

    name = student["name"]
    codes = student["codes"]

    # Create folder for the student
    student_folder = os.path.join("student-certificate", name)
    os.makedirs(student_folder, exist_ok=True)

    # Create 3 QR codes
    for code in codes:

        # Create unique certificate URL
        url = f"{BASE_URL}/{name}-{code}"

        # Create QR code
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )

        qr.add_data(url)
        qr.make(fit=True)

        # Generate PNG
        img = qr.make_image()

        # Save QR code
        file_path = os.path.join(
            student_folder,
            f"{code}.png"
        )

        img.save(file_path)

        print(f"Created: {file_path}")


print("All QR codes created successfully!")