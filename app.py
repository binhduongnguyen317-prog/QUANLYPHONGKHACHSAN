import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
from pathlib import Path

# =========================================================
# CẤU HÌNH
# =========================================================
st.set_page_config(
    page_title="Hotel Management",
    page_icon="🏨",
    layout="wide"
)

DB = Path("hotel.db")


# =========================================================
# DATABASE
# =========================================================
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def execute(sql, params=(), fetch=False):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params)

    result = cur.fetchall() if fetch else None

    conn.commit()
    conn.close()

    return result


def init_database():

    conn = get_db()
    cur = conn.cursor()

    # PHÒNG
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            price REAL NOT NULL,
            floor INTEGER NOT NULL,
            status TEXT DEFAULT 'Trống'
        )
    """)

    # KHÁCH
    cur.execute("""
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            id_card TEXT,
            phone TEXT,
            email TEXT,
            address TEXT
        )
    """)

    # ĐẶT PHÒNG
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,
            deposit REAL DEFAULT 0,
            status TEXT DEFAULT 'Đã đặt',
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # DỊCH VỤ
    cur.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL
        )
    """)

    # DỊCH VỤ ĐÃ SỬ DỤNG
    cur.execute("""
        CREATE TABLE IF NOT EXISTS service_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1
        )
    """)

    # THANH TOÁN
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            note TEXT,
            paid_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    # -----------------------------------------------------
    # DỮ LIỆU PHÒNG MẪU
    # -----------------------------------------------------

    count = cur.execute(
        "SELECT COUNT(*) FROM rooms"
    ).fetchone()[0]

    if count == 0:

        rooms = []

        for floor in range(1, 4):

            for number in range(1, 7):

                room_number = f"{floor}{number:02d}"

                if number <= 2:
                    room_type = "Standard"
                    price = 650000

                elif number <= 4:
                    room_type = "Deluxe"
                    price = 850000

                elif number == 5:
                    room_type = "Suite"
                    price = 1200000

                else:
                    room_type = "Villa"
                    price = 1800000

                rooms.append(
                    (
                        room_number,
                        room_type,
                        price,
                        floor,
                        "Trống"
                    )
                )

        cur.executemany("""
            INSERT INTO rooms
            (room_number, room_type, price, floor, status)
            VALUES (?, ?, ?, ?, ?)
        """, rooms)

    # -----------------------------------------------------
    # DỊCH VỤ MẪU
    # -----------------------------------------------------

    count = cur.execute(
        "SELECT COUNT(*) FROM services"
    ).fetchone()[0]

    if count == 0:

        services = [
            ("Bữa sáng", 120000),
            ("Nước suối", 20000),
            ("Giặt ủi", 80000),
            ("Thuê xe máy", 150000),
            ("Taxi", 350000),
            ("Spa", 400000)
        ]

        cur.executemany("""
            INSERT INTO services
            (name, price)
            VALUES (?, ?)
        """, services)

    conn.commit()
    conn.close()


# =========================================================
# HÀM TIỆN ÍCH
# =========================================================
def money(value):

    return f"{value:,.0f} ₫"


def calculate_nights(check_in, check_out):

    start = datetime.strptime(
        check_in, "%Y-%m-%d"
    ).date()

    end = datetime.strptime(
        check_out, "%Y-%m-%d"
    ).date()

    return max((end - start).days, 1)


def update_room_status():

    # Đưa phòng không còn khách về trống
    execute("""
        UPDATE rooms
        SET status = 'Trống'
        WHERE id NOT IN (
            SELECT room_id
            FROM bookings
            WHERE status = 'Đang ở'
        )
        AND status != 'Bảo trì'
    """)

    # Phòng đang ở
    execute("""
        UPDATE rooms
        SET status = 'Đang ở'
        WHERE id IN (
            SELECT room_id
            FROM bookings
            WHERE status = 'Đang ở'
        )
    """)

    # Phòng đã đặt
    execute("""
        UPDATE rooms
        SET status = 'Đã đặt'
        WHERE id IN (
            SELECT room_id
            FROM bookings
            WHERE status = 'Đã đặt'
        )
        AND status != 'Đang ở'
    """)


def get_booking_total(booking_id):

    booking = execute("""
        SELECT b.*, r.price
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.id = ?
    """, (booking_id,), True)

    if not booking:
        return 0

    booking = booking[0]

    room_total = (
        booking["price"]
        * calculate_nights(
            booking["check_in"],
            booking["check_out"]
        )
    )

    service_total = execute("""
        SELECT COALESCE(
            SUM(so.quantity * s.price), 0
        ) AS total
        FROM service_orders so
        JOIN services s
        ON so.service_id = s.id
        WHERE so.booking_id = ?
    """, (booking_id,), True)[0]["total"]

    return room_total + service_total


# =========================================================
# KHỞI TẠO
# =========================================================
init_database()
update_room_status()


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("🏨 HOTEL SYSTEM")

menu = st.sidebar.radio(
    "MENU",
    [
        "📊 Dashboard",
        "🛏️ Quản lý phòng",
        "👤 Khách hàng",
        "📅 Đặt phòng",
        "🛎️ Check-in / Check-out",
        "🧾 Dịch vụ",
        "💰 Thanh toán",
        "📈 Báo cáo"
    ]
)

st.sidebar.divider()

st.sidebar.info(
    "Hotel Management\n\n"
    "Python + Streamlit + SQLite"
)


# =========================================================
# DASHBOARD
# =========================================================
if menu == "📊 Dashboard":

    st.title("📊 DASHBOARD")

    rooms = execute(
        "SELECT * FROM rooms",
        fetch=True
    )

    total_rooms = len(rooms)

    empty_rooms = sum(
        r["status"] == "Trống"
        for r in rooms
    )

    occupied_rooms = sum(
        r["status"] == "Đang ở"
        for r in rooms
    )

    booked_rooms = sum(
        r["status"] == "Đã đặt"
        for r in rooms
    )

    today = date.today().isoformat()

    revenue = execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM payments
        WHERE DATE(paid_at) = DATE(?)
    """, (today,), True)[0]["total"]

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "🏨 Tổng phòng",
        total_rooms
    )

    c2.metric(
        "🟢 Phòng trống",
        empty_rooms
    )

    c3.metric(
        "🔴 Đang ở",
        occupied_rooms
    )

    c4.metric(
        "🟡 Đã đặt",
        booked_rooms
    )

    c5.metric(
        "💰 Doanh thu hôm nay",
        money(revenue)
    )

    st.divider()

    st.subheader("Tình trạng phòng")

    data = []

    for r in rooms:

        data.append({
            "Phòng": r["room_number"],
            "Loại phòng": r["room_type"],
            "Giá / đêm": money(r["price"]),
            "Tầng": r["floor"],
            "Trạng thái": r["status"]
        })

    st.dataframe(
        pd.DataFrame(data),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# QUẢN LÝ PHÒNG
# =========================================================
elif menu == "🛏️ Quản lý phòng":

    st.title("🛏️ QUẢN LÝ PHÒNG")

    tab1, tab2 = st.tabs(
        ["📋 Danh sách phòng", "➕ Thêm phòng"]
    )

    # -----------------------------------------------------
    # DANH SÁCH
    # -----------------------------------------------------

    with tab1:

        rooms = execute("""
            SELECT *
            FROM rooms
            ORDER BY floor, room_number
        """, fetch=True)

        data = []

        for r in rooms:

            data.append({
                "ID": r["id"],
                "Phòng": r["room_number"],
                "Loại": r["room_type"],
                "Giá": money(r["price"]),
                "Tầng": r["floor"],
                "Trạng thái": r["status"]
            })

        st.dataframe(
            pd.DataFrame(data),
            use_container_width=True,
            hide_index=True
        )

        st.subheader("✏️ Chỉnh sửa phòng")

        if rooms:

            room_map = {
                f'{r["room_number"]} - {r["room_type"]}':
                r["id"]
                for r in rooms
            }

            selected = st.selectbox(
                "Chọn phòng",
                list(room_map.keys())
            )

            room_id = room_map[selected]

            room = execute(
                "SELECT * FROM rooms WHERE id=?",
                (room_id,),
                True
            )[0]

            c1, c2, c3 = st.columns(3)

            new_type = c1.selectbox(
                "Loại phòng",
                [
                    "Standard",
                    "Deluxe",
                    "Suite",
                    "Villa"
                ],
                index=[
                    "Standard",
                    "Deluxe",
                    "Suite",
                    "Villa"
                ].index(room["room_type"])
            )

            new_price = c2.number_input(
                "Giá phòng",
                min_value=0.0,
                value=float(room["price"]),
                step=50000.0
            )

            new_status = c3.selectbox(
                "Trạng thái",
                [
                    "Trống",
                    "Đã đặt",
                    "Đang ở",
                    "Bảo trì"
                ],
                index=[
                    "Trống",
                    "Đã đặt",
                    "Đang ở",
                    "Bảo trì"
                ].index(room["status"])
            )

            if st.button(
                "💾 Lưu thay đổi",
                use_container_width=True
            ):

                execute("""
                    UPDATE rooms
                    SET room_type=?,
                        price=?,
                        status=?
                    WHERE id=?
                """, (
                    new_type,
                    new_price,
                    new_status,
                    room_id
                ))

                st.success(
                    "Đã cập nhật phòng!"
                )

                st.rerun()

    # -----------------------------------------------------
    # THÊM PHÒNG
    # -----------------------------------------------------

    with tab2:

        with st.form("add_room"):

            c1, c2, c3, c4 = st.columns(4)

            room_number = c1.text_input(
                "Số phòng"
            )

            room_type = c2.selectbox(
                "Loại phòng",
                [
                    "Standard",
                    "Deluxe",
                    "Suite",
                    "Villa"
                ]
            )

            price = c3.number_input(
                "Giá / đêm",
                min_value=0.0,
                value=650000.0,
                step=50000.0
            )

            floor = c4.number_input(
                "Tầng",
                min_value=1,
                value=1
            )

            submit = st.form_submit_button(
                "➕ Thêm phòng"
            )

            if submit:

                try:

                    execute("""
                        INSERT INTO rooms
                        (room_number,room_type,price,floor,status)
                        VALUES (?,?,?,?,?)
                    """, (
                        room_number,
                        room_type,
                        price,
                        floor,
                        "Trống"
                    ))

                    st.success(
                        "Thêm phòng thành công!"
                    )

                    st.rerun()

                except sqlite3.IntegrityError:

                    st.error(
                        "Số phòng đã tồn tại!"
                    )


# =========================================================
# KHÁCH HÀNG
# =========================================================
elif menu == "👤 Khách hàng":

    st.title("👤 QUẢN LÝ KHÁCH HÀNG")

    with st.expander(
        "➕ Thêm khách hàng",
        expanded=True
    ):

        with st.form("guest_form"):

            c1, c2 = st.columns(2)

            name = c1.text_input(
                "Họ và tên *"
            )

            id_card = c2.text_input(
                "CCCD / Hộ chiếu"
            )

            c3, c4 = st.columns(2)

            phone = c3.text_input(
                "Số điện thoại"
            )

            email = c4.text_input(
                "Email"
            )

            address = st.text_input(
                "Địa chỉ"
            )

            submit = st.form_submit_button(
                "💾 Lưu khách hàng"
            )

            if submit:

                if not name.strip():

                    st.error(
                        "Vui lòng nhập họ tên!"
                    )

                else:

                    execute("""
                        INSERT INTO guests
                        (name,id_card,phone,email,address)
                        VALUES (?,?,?,?,?)
                    """, (
                        name,
                        id_card,
                        phone,
                        email,
                        address
                    ))

                    st.success(
                        "Đã thêm khách hàng!"
                    )

                    st.rerun()

    st.divider()

    search = st.text_input(
        "🔎 Tìm khách hàng"
    )

    if search:

        guests = execute("""
            SELECT *
            FROM guests
            WHERE name LIKE ?
               OR id_card LIKE ?
               OR phone LIKE ?
            ORDER BY id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ), True)

    else:

        guests = execute("""
            SELECT *
            FROM guests
            ORDER BY id DESC
        """, fetch=True)

    data = []

    for g in guests:

        data.append({
            "ID": g["id"],
            "Họ tên": g["name"],
            "CCCD / Hộ chiếu": g["id_card"],
            "SĐT": g["phone"],
            "Email": g["email"],
            "Địa chỉ": g["address"]
        })

    st.dataframe(
        pd.DataFrame(data),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# ĐẶT PHÒNG
# =========================================================
elif menu == "📅 Đặt phòng":

    st.title("📅 ĐẶT PHÒNG")

    guests = execute(
        "SELECT * FROM guests ORDER BY name",
        fetch=True
    )

    rooms = execute("""
        SELECT *
        FROM rooms
        WHERE status = 'Trống'
        ORDER BY room_number
    """, fetch=True)

    if not guests:

        st.warning(
            "Chưa có khách hàng. "
            "Hãy thêm khách hàng trước."
        )

    elif not rooms:

        st.warning(
            "Hiện không có phòng trống."
        )

    else:

        guest_map = {
            f'{g["name"]} - {g["phone"] or "Không có SĐT"}':
            g["id"]
            for g in guests
        }

        room_map = {
            f'{r["room_number"]} - '
            f'{r["room_type"]} - '
            f'{money(r["price"])}':
            r["id"]
            for r in rooms
        }

        with st.form("booking_form"):

            guest = st.selectbox(
                "👤 Khách hàng",
                list(guest_map.keys())
            )

            room = st.selectbox(
                "🛏️ Phòng",
                list(room_map.keys())
            )

            c1, c2 = st.columns(2)

            check_in = c1.date_input(
                "Ngày nhận phòng",
                value=date.today()
            )

            check_out = c2.date_input(
                "Ngày trả phòng",
                value=date.today()
            )

            c3, c4 = st.columns(2)

            adults = c3.number_input(
                "Người lớn",
                min_value=1,
                value=1
            )

            children = c4.number_input(
                "Trẻ em",
                min_value=0,
                value=0
            )

            deposit = st.number_input(
                "Tiền cọc",
                min_value=0.0,
                value=0.0,
                step=100000.0
            )

            note = st.text_area(
                "Ghi chú"
            )

            submit = st.form_submit_button(
                "📅 Tạo đặt phòng"
            )

            if submit:

                if check_out <= check_in:

                    st.error(
                        "Ngày trả phải sau ngày nhận!"
                    )

                else:

                    room_id = room_map[room]

                    overlap = execute("""
                        SELECT id
                        FROM bookings
                        WHERE room_id=?
                        AND status IN ('Đã đặt','Đang ở')
                        AND DATE(check_in) < DATE(?)
                        AND DATE(check_out) > DATE(?)
                    """, (
                        room_id,
                        check_out.isoformat(),
                        check_in.isoformat()
                    ), True)

                    if overlap:

                        st.error(
                            "Phòng đã được đặt "
                            "trong khoảng thời gian này!"
                        )

                    else:

                        execute("""
                            INSERT INTO bookings
                            (
                                guest_id,
                                room_id,
                                check_in,
                                check_out,
                                adults,
                                children,
                                deposit,
                                status,
                                note
                            )
                            VALUES (?,?,?,?,?,?,?,?,?)
                        """, (
                            guest_map[guest],
                            room_id,
                            check_in.isoformat(),
                            check_out.isoformat(),
                            adults,
                            children,
                            deposit,
                            "Đã đặt",
                            note
                        ))

                        execute("""
                            UPDATE rooms
                            SET status='Đã đặt'
                            WHERE id=?
                        """, (room_id,))

                        st.success(
                            "Đặt phòng thành công!"
                        )

                        st.rerun()

    st.divider()

    st.subheader(
        "📋 Danh sách đặt phòng"
    )

    bookings = execute("""
        SELECT
            b.id,
            g.name,
            r.room_number,
            r.room_type,
            b.check_in,
            b.check_out,
            b.adults,
            b.children,
            b.deposit,
            b.status,
            b.note
        FROM bookings b
        JOIN guests g
            ON b.guest_id=g.id
        JOIN rooms r
            ON b.room_id=r.id
        ORDER BY b.id DESC
    """, fetch=True)

    data = []

    for b in bookings:

        data.append({
            "ID": b["id"],
            "Khách": b["name"],
            "Phòng": b["room_number"],
            "Loại": b["room_type"],
            "Nhận": b["check_in"],
            "Trả": b["check_out"],
            "Người lớn": b["adults"],
            "Trẻ em": b["children"],
            "Tiền cọc": money(b["deposit"]),
            "Trạng thái": b["status"],
            "Ghi chú": b["note"]
        })

    st.dataframe(
        pd.DataFrame(data),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# CHECK-IN / CHECK-OUT
# =========================================================
elif menu == "🛎️ Check-in / Check-out":

    st.title(
        "🛎️ CHECK-IN / CHECK-OUT"
    )

    bookings = execute("""
        SELECT
            b.*,
            g.name,
            g.id_card,
            g.phone,
            r.room_number,
            r.room_type,
            r.price
        FROM bookings b
        JOIN guests g
            ON b.guest_id=g.id
        JOIN rooms r
            ON b.room_id=r.id
        WHERE b.status IN ('Đã đặt','Đang ở')
        ORDER BY b.check_in
    """, fetch=True)

    if not bookings:

        st.info(
            "Không có booking cần xử lý."
        )

    else:

        booking_map = {
            f'#{b["id"]} | '
            f'Phòng {b["room_number"]} | '
            f'{b["name"]} | '
            f'{b["check_in"]} → {b["check_out"]} | '
            f'{b["status"]}':
            b["id"]
            for b in bookings
        }

        selected = st.selectbox(
            "Chọn booking",
            list(booking_map.keys())
        )

        booking_id = booking_map[selected]

        booking = next(
            b for b in bookings
            if b["id"] == booking_id
        )

        nights = calculate_nights(
            booking["check_in"],
            booking["check_out"]
        )

        room_total = (
            nights * booking["price"]
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "👤 Khách",
            booking["name"]
        )

        c2.metric(
            "🛏️ Phòng",
            booking["room_number"]
        )

        c3.metric(
            "🌙 Số đêm",
            nights
        )

        c4.metric(
            "💰 Tiền phòng",
            money(room_total)
        )

        st.divider()

        if booking["status"] == "Đã đặt":

            st.subheader(
                "🟢 Xác nhận Check-in"
            )

            st.write(
                f"**CCCD/Hộ chiếu:** "
                f"{booking['id_card'] or 'Chưa nhập'}"
            )

            st.write(
                f"**Số điện thoại:** "
                f"{booking['phone'] or 'Chưa nhập'}"
            )

            if st.button(
                "🟢 CHECK-IN",
                use_container_width=True
            ):

                execute("""
                    UPDATE bookings
                    SET status='Đang ở'
                    WHERE id=?
                """, (booking_id,))

                execute("""
                    UPDATE rooms
                    SET status='Đang ở'
                    WHERE id=?
                """, (booking["room_id"],))

                st.success(
                    "Check-in thành công!"
                )

                st.rerun()

        else:

            st.subheader(
                "🔴 Check-out"
            )

            total = get_booking_total(
                booking_id
            )

            paid = execute("""
                SELECT COALESCE(
                    SUM(amount),0
                ) AS total
                FROM payments
                WHERE booking_id=?
            """, (booking_id,), True)[0]["total"]

            balance = total - paid

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Tổng hóa đơn",
                money(total)
            )

            c2.metric(
                "Đã thanh toán",
                money(paid)
            )

            c3.metric(
                "Còn lại",
                money(max(balance, 0))
            )

            if st.button(
                "🔴 CHECK-OUT",
                use_container_width=True
            ):

                execute("""
                    UPDATE bookings
                    SET status='Đã trả'
                    WHERE id=?
                """, (booking_id,))

                execute("""
                    UPDATE rooms
                    SET status='Trống'
                    WHERE id=?
                """, (booking["room_id"],))

                st.success(
                    "Check-out thành công!"
                )

                st.rerun()


# =========================================================
# DỊCH VỤ
# =========================================================
elif menu == "🧾 Dịch vụ":

    st.title(
        "🧾 QUẢN LÝ DỊCH VỤ"
    )

    tab1, tab2 = st.tabs(
        [
            "➕ Thêm dịch vụ vào phòng",
            "⚙️ Danh mục dịch vụ"
        ]
    )

    # -----------------------------------------------------
    # THÊM DỊCH VỤ
    # -----------------------------------------------------

    with tab1:

        bookings = execute("""
            SELECT
                b.id,
                g.name,
                r.room_number
            FROM bookings b
            JOIN guests g
                ON b.guest_id=g.id
            JOIN rooms r
                ON b.room_id=r.id
            WHERE b.status IN ('Đã đặt','Đang ở')
        """, fetch=True)

        services = execute(
            "SELECT * FROM services ORDER BY name",
            fetch=True
        )

        if bookings and services:

            booking_map = {
                f'#{b["id"]} | '
                f'Phòng {b["room_number"]} | '
                f'{b["name"]}':
                b["id"]
                for b in bookings
            }

            service_map = {
                f'{s["name"]} - {money(s["price"])}':
                s["id"]
                for s in services
            }

            with st.form(
                "service_order"
            ):

                booking = st.selectbox(
                    "Booking",
                    list(booking_map.keys())
                )

                service = st.selectbox(
                    "Dịch vụ",
                    list(service_map.keys())
                )

                quantity = st.number_input(
                    "Số lượng",
                    min_value=1,
                    value=1
                )

                submit = st.form_submit_button(
                    "➕ Thêm dịch vụ"
                )

                if submit:

                    execute("""
                        INSERT INTO service_orders
                        (booking_id,service_id,quantity)
                        VALUES (?,?,?)
                    """, (
                        booking_map[booking],
                        service_map[service],
                        quantity
                    ))

                    st.success(
                        "Đã thêm dịch vụ!"
                    )

                    st.rerun()

        st.divider()

        orders = execute("""
            SELECT
                so.id,
                so.booking_id,
                g.name,
                r.room_number,
                s.name AS service,
                so.quantity,
                s.price,
                so.quantity*s.price AS total
            FROM service_orders so
            JOIN bookings b
                ON so.booking_id=b.id
            JOIN guests g
                ON b.guest_id=g.id
            JOIN rooms r
                ON b.room_id=r.id
            JOIN services s
                ON so.service_id=s.id
            ORDER BY so.id DESC
        """, fetch=True)

        data = []

        for o in orders:

            data.append({
                "ID": o["id"],
                "Booking": o["booking_id"],
                "Khách": o["name"],
                "Phòng": o["room_number"],
                "Dịch vụ": o["service"],
                "SL": o["quantity"],
                "Đơn giá": money(o["price"]),
                "Thành tiền": money(o["total"])
            })

        st.dataframe(
            pd.DataFrame(data),
            use_container_width=True,
            hide_index=True
        )

    # -----------------------------------------------------
    # DANH MỤC DỊCH VỤ
    # -----------------------------------------------------

    with tab2:

        with st.form(
            "new_service"
        ):

            name = st.text_input(
                "Tên dịch vụ"
            )

            price = st.number_input(
                "Giá dịch vụ",
                min_value=0.0,
                value=100000.0,
                step=10000.0
            )

            submit = st.form_submit_button(
                "➕ Thêm dịch vụ"
            )

            if submit:

                try:

                    execute("""
                        INSERT INTO services
                        (name,price)
                        VALUES (?,?)
                    """, (
                        name,
                        price
                    ))

                    st.success(
                        "Đã thêm dịch vụ!"
                    )

                    st.rerun()

                except sqlite3.IntegrityError:

                    st.error(
                        "Dịch vụ đã tồn tại!"
                    )

        services = execute(
            "SELECT * FROM services",
            fetch=True
        )

        data = []

        for s in services:

            data.append({
                "ID": s["id"],
                "Dịch vụ": s["name"],
                "Giá": money(s["price"])
            })

        st.dataframe(
            pd.DataFrame(data),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# THANH TOÁN
# =========================================================
elif menu == "💰 Thanh toán":

    st.title(
        "💰 THANH TOÁN"
    )

    bookings = execute("""
        SELECT
            b.id,
            g.name,
            r.room_number,
            b.status
        FROM bookings b
        JOIN guests g
            ON b.guest_id=g.id
        JOIN rooms r
            ON b.room_id=r.id
        WHERE b.status IN
            ('Đã đặt','Đang ở','Đã trả')
        ORDER BY b.id DESC
    """, fetch=True)

    if not bookings:

        st.info(
            "Chưa có booking."
        )

    else:

        booking_map = {
            f'#{b["id"]} | '
            f'Phòng {b["room_number"]} | '
            f'{b["name"]} | '
            f'{b["status"]}':
            b["id"]
            for b in bookings
        }

        selected = st.selectbox(
            "Chọn booking",
            list(booking_map.keys())
        )

        booking_id = booking_map[selected]

        total = get_booking_total(
            booking_id
        )

        paid = execute("""
            SELECT COALESCE(
                SUM(amount),0
            ) AS total
            FROM payments
            WHERE booking_id=?
        """, (booking_id,), True)[0]["total"]

        balance = total - paid

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Tổng hóa đơn",
            money(total)
        )

        c2.metric(
            "Đã thanh toán",
            money(paid)
        )

        c3.metric(
            "Còn lại",
            money(max(balance, 0))
        )

        st.divider()

        if balance > 0:

            with st.form(
                "payment_form"
            ):

                amount = st.number_input(
                    "Số tiền thanh toán",
                    min_value=0.0,
                    max_value=float(balance),
                    value=float(balance),
                    step=50000.0
                )

                method = st.selectbox(
                    "Phương thức",
                    [
                        "Tiền mặt",
                        "Chuyển khoản",
                        "Thẻ"
                    ]
                )

                note = st.text_input(
                    "Ghi chú"
                )

                submit = st.form_submit_button(
                    "💳 Thanh toán"
                )

                if submit:

                    if amount <= 0:

                        st.error(
                            "Số tiền phải lớn hơn 0."
                        )

                    else:

                        execute("""
                            INSERT INTO payments
                            (booking_id,amount,method,note)
                            VALUES (?,?,?,?)
                        """, (
                            booking_id,
                            amount,
                            method,
                            note
                        ))

                        st.success(
                            "Thanh toán thành công!"
                        )

                        st.rerun()

        else:

            st.success(
                "✅ Booking đã thanh toán đủ."
            )

        st.subheader(
            "📋 Lịch sử thanh toán"
        )

        payments = execute("""
            SELECT *
            FROM payments
            WHERE booking_id=?
            ORDER BY id DESC
        """, (booking_id,), True)

        data = []

        for p in payments:

            data.append({
                "ID": p["id"],
                "Số tiền": money(p["amount"]),
                "Phương thức": p["method"],
                "Thời gian": p["paid_at"],
                "Ghi chú": p["note"]
            })

        st.dataframe(
            pd.DataFrame(data),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# BÁO CÁO
# =========================================================
elif menu == "📈 Báo cáo":

    st.title(
        "📈 BÁO CÁO"
    )

    c1, c2 = st.columns(2)

    start = c1.date_input(
        "Từ ngày",
        value=date.today().replace(day=1)
    )

    end = c2.date_input(
        "Đến ngày",
        value=date.today()
    )

    if start > end:

        st.error(
            "Ngày bắt đầu phải nhỏ hơn ngày kết thúc."
        )

    else:

        revenue = execute("""
            SELECT COALESCE(
                SUM(amount),0
            ) AS total
            FROM payments
            WHERE DATE(paid_at)
            BETWEEN DATE(?) AND DATE(?)
        """, (
            start.isoformat(),
            end.isoformat()
        ), True)[0]["total"]

        bookings_count = execute("""
            SELECT COUNT(*) AS total
            FROM bookings
            WHERE DATE(created_at)
            BETWEEN DATE(?) AND DATE(?)
        """, (
            start.isoformat(),
            end.isoformat()
        ), True)[0]["total"]

        total_guests = execute("""
            SELECT COUNT(*) AS total
            FROM guests
        """, fetch=True)[0]["total"]

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "💰 Doanh thu",
            money(revenue)
        )

        c2.metric(
            "📅 Booking",
            bookings_count
        )

        c3.metric(
            "👤 Tổng khách",
            total_guests
        )

        st.divider()

        st.subheader(
            "💳 Doanh thu theo phương thức"
        )

        revenue_data = execute("""
            SELECT
                method,
                SUM(amount) AS total
            FROM payments
            WHERE DATE(paid_at)
            BETWEEN DATE(?) AND DATE(?)
            GROUP BY method
        """, (
            start.isoformat(),
            end.isoformat()
        ), True)

        if revenue_data:

            df = pd.DataFrame(
                [dict(x) for x in revenue_data]
            )

            st.bar_chart(
                df.set_index("method")["total"]
            )

        else:

            st.info(
                "Chưa có doanh thu trong khoảng thời gian này."
            )

        st.subheader(
            "📊 Booking theo trạng thái"
        )

        status_data = execute("""
            SELECT
                status,
                COUNT(*) AS total
            FROM bookings
            GROUP BY status
        """, fetch=True)

        if status_data:

            df = pd.DataFrame(
                [dict(x) for x in status_data]
            )

            df.columns = [
                "Trạng thái",
                "Số lượng"
            ]

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

st.sidebar.divider()

st.sidebar.caption(
    "© 2026 Hotel Management System"
)
