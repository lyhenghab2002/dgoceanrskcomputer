Unknown column 'session_id' in 'where clause'Unknown column 'session_id' in 'where clause'from bakong_khqr import KHQR

khqr = KHQR("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTU5YjgzZWI2NjRhNDBlMyJ9LCJpYXQiOjE3NjA0NjAxMDEsImV4cCI6MTc2ODIzNjEwMX0.tL1hT8aLC-Oca_KW8ZCCl6NK4xI62CsaC1_dLawi668")

# make qr

# qr_string = khqr.create_qr(
#     bank_account="kong_dalin1@aclb",
#     merchant_name="Kong Dalin",
#     merchant_city="Phnom Penh",
#     amount=1000.00,
#     currency="KHR",
#     store_label="Kong Dalin Store",
#     phone_number="0123456789",
#     bill_number="1234567890",
#     terminal_label="WebQR",
#     static=False,
# )

# print("QR String", qr_string)

# make md5

# md5 = khqr.generate_md5(
#     qr=qr_string

# )
# print("MD5", md5)

# check_result = khqr.check_payment(
#     md5="d32d3a293d2296c31ebe1769b3ce29fa"
# )
# print("Check Result", check_result)

md5_list = [
    "d32d3a293d2296c31ebe1769b3ce29fa",
    "695aac3b7a401dc7547a0483d327bd0a",
    "64b94ca68a9f549407a65940b24cf1a4",
    "b725317288c0f1386ab4b6ac5caa08e4",
    "9a64fe9e291db51a69a52a34c183ac72",
    "bec1c87dc36f47a660c0ae1d5fb8d119"
]

# for md5 in md5_list:
#     check_result = khqr.check_payment(md5=md5)
#     print(f"Check Result for {md5}: {check_result}")


check_result_list = khqr.check_bulk_payments(
    md5_list=md5_list

)
print("Check Result List", check_result_list)