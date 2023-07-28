import sys
import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QMessageBox, QLineEdit, QTableWidget, QTableWidgetItem, QDialog, QHBoxLayout
from PyQt5.QtGui import QDoubleValidator, QPixmap
from PyQt5.QtCore import Qt, QTimer, QTime, QDate

class ShowCustomersDialog(QDialog):
    def __init__(self, data, conn):
        super().__init__()
        self.setWindowTitle('Müşterileri Göster')
        self.setGeometry(100, 100, 925, 400)
        self.conn = conn

        layout = QVBoxLayout()
        self.table_widget = QTableWidget()
        self.table_widget.setRowCount(len(data))
        self.table_widget.setColumnCount(7)
        headers = ['No', 'Sayaç Adı', 'Birim Fiyat (TL/kWh)', 'İlk Endeks', 'Son Endeks', 'Endeks Farkı', 'Toplam Tutar(TL)']
        self.table_widget.setHorizontalHeaderLabels(headers)
        for row_num, row_data in enumerate(data):
            for col_num, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                if col_num == 0:
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(Qt.Unchecked)
                self.table_widget.setItem(row_num, col_num, item)

            total_amount = float(row_data[2]) * (float(row_data[4]) - float(row_data[3]) - float(row_data[5]))
            total_amount_item = QTableWidgetItem(str(total_amount))
            total_amount_item.setFlags(Qt.ItemIsEnabled)
            self.table_widget.setItem(row_num, 6, total_amount_item)

        layout.addWidget(self.table_widget)

        button_close = QPushButton('Kapat')
        button_close.clicked.connect(self.close)
        layout.addWidget(button_close)

        button_delete_customer = QPushButton('Müşteriyi Sil')
        button_delete_customer.clicked.connect(self.delete_customer)
        layout.addWidget(button_delete_customer)

        button_select_all = QPushButton('Tümünü Seç')
        button_select_all.clicked.connect(self.select_all_customers)
        layout.addWidget(button_select_all)

        self.setLayout(layout)

    def delete_customer(self):
        checked_items = []
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 0)
            if item.checkState() == Qt.Checked:
                checked_items.append(row)

        if not checked_items:
            QMessageBox.warning(self, 'Hata', 'Lütfen silmek istediğiniz müşteriyi seçin.', QMessageBox.Ok)
        else:
            for row in checked_items:
                customer_id = int(self.table_widget.item(row, 0).text())
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute('DELETE FROM sayaclar WHERE id = ?', (customer_id,))
                    self.conn.commit()

            self.reorder_customer_numbers()  # Müşteri numaralarını yeniden düzenle
            QMessageBox.information(self, 'Silindi', 'Seçili müşteriler başarıyla silindi.', QMessageBox.Ok)
            self.update_table()

    def select_all_customers(self):
        # Eğer tüm satırlar seçiliyse, tüm seçimleri iptal et
        if all(self.table_widget.item(row, 0).checkState() == Qt.Checked for row in range(self.table_widget.rowCount())):
            for row in range(self.table_widget.rowCount()):
                item = self.table_widget.item(row, 0)
                item.setCheckState(Qt.Unchecked)
        else:
            # Tüm satırları seç
            for row in range(self.table_widget.rowCount()):
                item = self.table_widget.item(row, 0)
                item.setCheckState(Qt.Checked)

    def update_table(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('SELECT id, ad, birim_fiyat, ilk_endeks, son_endeks, endeks_farki FROM sayaclar')
            data = cursor.fetchall()

            self.table_widget.setRowCount(len(data))

            for row_num, row_data in enumerate(data):
                for col_num, cell_data in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_data))
                    if col_num == 0:
                        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                        item.setCheckState(Qt.Unchecked)
                    self.table_widget.setItem(row_num, col_num, item)

                total_amount = float(row_data[2]) * (float(row_data[4]) - float(row_data[3]) - float(row_data[5]))
                total_amount_item = QTableWidgetItem(str(total_amount))
                total_amount_item.setFlags(Qt.ItemIsEnabled)
                self.table_widget.setItem(row_num, 6, total_amount_item)

    def reorder_customer_numbers(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('SELECT id FROM sayaclar ORDER BY id ASC')
            customer_ids = cursor.fetchall()

            for index, customer_id in enumerate(customer_ids, start=1):
                cursor.execute('UPDATE sayaclar SET id=? WHERE id=?', (index, customer_id[0]))

            self.conn.commit()

class ElectricityMeterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Elektrik Sayaç Okuma Uygulaması')
        self.setGeometry(100, 100, 600, 400)

        self.label_name = QLabel('Sayaç Adı:')
        self.line_edit_name = QLineEdit()

        self.label_unit_price = QLabel('Birim Fiyat (TL/kWh):')
        self.line_edit_unit_price = QLineEdit()
        self.line_edit_unit_price.setValidator(QDoubleValidator())

        self.label_start_index = QLabel('İlk Endeks:')
        self.line_edit_start_index = QLineEdit()
        self.line_edit_start_index.setValidator(QDoubleValidator())

        self.label_end_index = QLabel('Son Endeks:')
        self.line_edit_end_index = QLineEdit()
        self.line_edit_end_index.setValidator(QDoubleValidator())

        self.label_endeks_farki = QLabel('Endeks Farkı:')
        self.line_edit_endeks_farki = QLineEdit()
        self.line_edit_endeks_farki.setValidator(QDoubleValidator())

        self.button_calculate = QPushButton('Hesapla')
        self.button_calculate.clicked.connect(self.calculate_total_amount)

        self.label_result = QLabel('')

        self.button_save = QPushButton('Kaydet')
        self.button_save.clicked.connect(self.save_data)

        self.button_show_customers = QPushButton('Müşterileri Göster')
        self.button_show_customers.clicked.connect(self.show_customers)

        self.table_widget = QTableWidget()

        layout = QVBoxLayout()
        logo_label = QLabel(self)
        pixmap = QPixmap("ugurlu_elektrik.png")
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        self.label_datetime = QLabel()
        self.label_datetime.setAlignment(Qt.AlignRight)
        layout.addWidget(self.label_datetime)

        self.datetime_timer = QTimer(self)
        self.datetime_timer.timeout.connect(self.update_datetime)
        self.datetime_timer.start(1000)

        layout.addWidget(self.label_name)
        layout.addWidget(self.line_edit_name)
        layout.addWidget(self.label_unit_price)
        layout.addWidget(self.line_edit_unit_price)
        layout.addWidget(self.label_start_index)
        layout.addWidget(self.line_edit_start_index)
        layout.addWidget(self.label_end_index)
        layout.addWidget(self.line_edit_end_index)
        layout.addWidget(self.label_endeks_farki)
        layout.addWidget(self.line_edit_endeks_farki)
        layout.addWidget(self.button_calculate)
        layout.addWidget(self.label_result)
        layout.addWidget(self.button_save)
        layout.addWidget(self.button_show_customers)
        developed_by_label = QLabel('Developed by Alperen', self)
        developed_by_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(developed_by_label)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.conn = sqlite3.connect('veritabani.db')
        self.create_table()

    def create_table(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('CREATE TABLE IF NOT EXISTS sayaclar (id INTEGER PRIMARY KEY, ad TEXT, birim_fiyat REAL, ilk_endeks REAL, son_endeks REAL, endeks_farki REAL)')

    def calculate_total_amount(self):
        try:
            name = self.line_edit_name.text()
            unit_price = float(self.line_edit_unit_price.text())
            start_index = float(self.line_edit_start_index.text())
            end_index = float(self.line_edit_end_index.text())
            index_diff = end_index - start_index
            endeks_farki = float(self.line_edit_endeks_farki.text())
            total_amount = unit_price * (index_diff - endeks_farki)
            self.label_result.setText(f"{name} için toplam tutar: {total_amount:.2f} TL")
            QMessageBox.information(self, 'Hesaplandı', f"{name} için toplam tutar hesaplandı.", QMessageBox.Ok)
        except ValueError:
            self.label_result.setText('Hatalı giriş! Lütfen geçerli sayısal değerler giriniz.')
            QMessageBox.warning(self, 'Hata', 'Hatalı giriş! Lütfen geçerli sayısal değerler giriniz.', QMessageBox.Ok)

    def save_data(self):
        try:
            name = self.line_edit_name.text()
            unit_price = float(self.line_edit_unit_price.text())
            start_index = float(self.line_edit_start_index.text())
            end_index = float(self.line_edit_end_index.text())
            endeks_farki = float(self.line_edit_endeks_farki.text())

            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('SELECT ad FROM sayaclar WHERE ad = ?', (name,))
                existing_customer = cursor.fetchone()

                if existing_customer:
                    reply = QMessageBox.question(self, 'Müşteri Var!', 'Aynı isimde müşteri bulunuyor. Güncellemek istiyor musunuz?', QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        cursor.execute('UPDATE sayaclar SET birim_fiyat=?, ilk_endeks=?, son_endeks=?, endeks_farki=? WHERE ad=?', (unit_price, start_index, end_index, endeks_farki, name))
                    else:
                        return
                else:
                    cursor.execute('INSERT INTO sayaclar (ad, birim_fiyat, ilk_endeks, son_endeks, endeks_farki) VALUES (?, ?, ?, ?, ?)',
                                   (name, unit_price, start_index, end_index, endeks_farki))
                self.conn.commit()

            self.reorder_customer_numbers()  # Müşteri numaralarını yeniden düzenle
            QMessageBox.information(self, 'Kaydedildi', 'Veriler veritabanına kaydedildi.', QMessageBox.Ok)
            self.line_edit_name.clear()
            self.line_edit_unit_price.clear()
            self.line_edit_start_index.clear()
            self.line_edit_end_index.clear()
            self.line_edit_endeks_farki.clear()
        except ValueError:
            QMessageBox.warning(self, 'Hata', 'Hatalı giriş! Lütfen geçerli sayısal değerler giriniz.', QMessageBox.Ok)

    def show_customers(self):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('SELECT id, ad, birim_fiyat, ilk_endeks, son_endeks, endeks_farki FROM sayaclar')
                data = cursor.fetchall()

                self.show_customers_dialog = ShowCustomersDialog(data, self.conn)
                self.show_customers_dialog.exec_()
                self.update_table()

        except sqlite3.Error as e:
            QMessageBox.warning(self, 'Hata', f'Veritabanından veriler alınamadı: {str(e)}', QMessageBox.Ok)

    def update_table(self):
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute('SELECT id, ad, birim_fiyat, ilk_endeks, son_endeks, endeks_farki FROM sayaclar')
                data = cursor.fetchall()

                self.table_widget.setRowCount(len(data))

                for row_num, row_data in enumerate(data):
                    for col_num, cell_data in enumerate(row_data):
                        item = QTableWidgetItem(str(cell_data))
                        if col_num == 0:
                            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                            item.setCheckState(Qt.Unchecked)
                        self.table_widget.setItem(row_num, col_num, item)

                    total_amount = float(row_data[2]) * (float(row_data[4]) - float(row_data[3]) - float(row_data[5]))
                    total_amount_item = QTableWidgetItem(str(total_amount))
                    total_amount_item.setFlags(Qt.ItemIsEnabled)
                    self.table_widget.setItem(row_num, 6, total_amount_item)

        except sqlite3.Error as e:
            QMessageBox.warning(self, 'Hata', f'Veritabanından veriler alınamadı: {str(e)}', QMessageBox.Ok)

    def reorder_customer_numbers(self):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('SELECT id FROM sayaclar ORDER BY id ASC')
            customer_ids = cursor.fetchall()

            for index, customer_id in enumerate(customer_ids, start=1):
                cursor.execute('UPDATE sayaclar SET id=? WHERE id=?', (index, customer_id[0]))

            self.conn.commit()

    def update_datetime(self):
        current_time = QTime.currentTime().toString("hh:mm:ss")
        current_date = QDate.currentDate().toString("dd.MM.yyyy")
        datetime_str = f"{current_time} - {current_date}"
        self.label_datetime.setText(datetime_str)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ElectricityMeterApp()
    window.show()
    sys.exit(app.exec_())
