import os
import qrcode


students = [
    {
        "name": "ahmed-atef-mohamed-ghareeb",
        "codes": ["fa0064", "fa0065", "fa0066"],
    },
    {
        "name": "mohamed-abdalaziz-mohamed-ahmed",
        "codes": ["fa0067", "fa0068", "fa0069"],
    },
    {
        "name": "mostafa-salah-abdelsalam-ahmed",
        "codes": ["fa0070", "fa0071", "fa0072"],
    },
    {
        "name": "ahmed-maher-ali-abdel-nabe",
        "codes": ["fa0073", "fa0074", "fa0075"],
    },
    {
        "name": "ali-elsayed-mohamed-mohamed",
        "codes": ["fa0076", "fa0077", "fa0078"],
    },
    {
        "name": "mohamed-ahmed-hassan",
        "codes": ["fa0079", "fa0080", "fa0081"],
    },
]


BASE_URL = "https://www.futureacademey.com/certificate"

# Create main certificate folder
os.makedirs("certificate", exist_ok=True)


for student in students:

    name = student["name"]
    codes = student["codes"]

    # Create folder for the student
    student_folder = os.path.join("certificate", name)
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