# -*- coding: utf-8 -*-
#!/usr/bin/env python3

import os
import logging
from dotenv import load_dotenv

import pymysql
import requests
from requests.auth import HTTPBasicAuth
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'homplast_admin')  # Default username if not set
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
WC_URL = os.getenv('WC_URL', 'https://homplast.com')
WC_CONSUMER_KEY = os.getenv('WC_CONSUMER_KEY')
WC_CONSUMER_SECRET = os.getenv('WC_CONSUMER_SECRET')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_persian_to_english(text):
    """Convert Persian/Arabic digits to English digits"""
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits + arabic_digits, english_digits * 2)
    return text.translate(translation_table)

def get_db_connection():
    try:
        return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME,
                              charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, autocommit=False)
    except Exception as e:
        logger.error(f"DB error: {e}")
        return None

def fetch_product_from_woocommerce(sku: str):
    try:
        url = f"{WC_URL}/wp-json/wc/v3/products"
        auth = HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
        response = requests.get(url, params={'sku': sku}, auth=auth, timeout=10)
        
        if response.status_code == 200:
            products = response.json()
            if products and len(products) > 0:
                product = products[0]
                name = product.get('name', f'Product {sku}')
                price = float(product.get('regular_price', 0))
                
                # Check stock status
                stock_status = product.get('stock_status', 'outofstock')
                stock_quantity = product.get('stock_quantity', 0)
                manage_stock = product.get('manage_stock', False)
                
                # Determine if product is in stock
                in_stock = stock_status == 'instock'
                
                # Calculate min_quantity based ONLY on price
                if price <= 30000:
                    min_quantity = 12
                elif 30000 < price <= 100000:
                    min_quantity = 6
                else:
                    min_quantity = 1
                
                logger.info(f"Product: {name}, Price: {price}, Min: {min_quantity}, Stock: {stock_status}, Qty: {stock_quantity}")
                return {
                    'product_id': sku, 
                    'name': name, 
                    'price': price, 
                    'min_quantity': min_quantity,
                    'in_stock': in_stock,
                    'stock_quantity': stock_quantity,
                    'manage_stock': manage_stock
                }
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def save_user(user_id, username=None, first_name=None, last_name=None):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE username = VALUES(username), first_name = VALUES(first_name), last_name = VALUES(last_name)"
            cursor.execute(sql, (user_id, username, first_name, last_name))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    finally:
        conn.close()

def get_user_info(user_id):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()

def update_user_phone(user_id, phone_number):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET phone_number = %s WHERE user_id = %s", (phone_number, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

def update_cart_quantity(user_id, product_id, new_quantity):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND product_id = %s", (new_quantity, user_id, product_id))
        conn.commit()
        return True
    finally:
        conn.close()

def add_to_cart(user_id, product_id, quantity):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT cart_id, quantity FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE cart SET quantity = %s WHERE cart_id = %s", (existing['quantity'] + quantity, existing['cart_id']))
            else:
                cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", (user_id, product_id, quantity))
        conn.commit()
        return True
    finally:
        conn.close()

def remove_from_cart(user_id, product_id):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        conn.commit()
        return True
    finally:
        conn.close()

def get_user_cart(user_id):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT c.cart_id, c.product_id, c.quantity, p.product_name, p.price FROM cart c LEFT JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s", (user_id,))
            return cursor.fetchall()
    finally:
        conn.close()

def clear_user_cart(user_id):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def save_product_to_db(product_info):
    conn = get_db_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO products (product_id, product_name, price) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE product_name = VALUES(product_name), price = VALUES(price)",
                          (product_info['product_id'], product_info['name'], product_info['price']))
        conn.commit()
        return True
    finally:
        conn.close()

def create_order(user_id, cart_items):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        total = sum(item['price'] * item['quantity'] for item in cart_items if item['price'])
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
            order_id = cursor.lastrowid
            for item in cart_items:
                cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                              (order_id, item['product_id'], item['quantity'], item['price']))
        conn.commit()
        return order_id
    except Exception as e:
        logger.error(f"Error: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_user_orders(user_id):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT o.order_id, o.total_amount, o.status, o.created_at, COUNT(oi.item_id) as item_count FROM orders o LEFT JOIN order_items oi ON o.order_id = oi.order_id WHERE o.user_id = %s GROUP BY o.order_id ORDER BY o.created_at DESC", (user_id,))
            return cursor.fetchall()
    finally:
        conn.close()

def format_cart(cart_items):
    if not cart_items:
        return "**🛒 سبد خرید خالی است.**"
    text = "**🛒 سبد خرید شما:**\n\n"
    total = 0
    for idx, item in enumerate(cart_items, 1):
        product_name = item.get('product_name') or f"محصول {item['product_id']}"
        price = item.get('price') or 0
        quantity = item['quantity']
        subtotal = price * quantity
        total += subtotal
        text += f"**{idx}- {product_name}**\n\n**{quantity} x {price:,.0f} = {subtotal:,.0f}**\n➖➖➖➖➖➖➖\n"
    text += f"\n**💰 مجموع: {total:,.0f} تومان**"
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT first_name FROM users WHERE user_id = %s", (user.id,))
                existing = cursor.fetchone()
                if not existing:
                    cursor.execute("INSERT INTO users (user_id, username) VALUES (%s, %s)", (user.id, user.username))
                    conn.commit()
                else:
                    cursor.execute("UPDATE users SET username = %s WHERE user_id = %s", (user.username, user.id))
                    conn.commit()
        finally:
            conn.close()
    
    if context.args and context.args[0].startswith('product_'):
        product_sku = context.args[0].replace('product_', '')
        await update.message.reply_text("**⏳ لطفاً صبر کنید...**", parse_mode='Markdown')
        product_info = fetch_product_from_woocommerce(product_sku)
        
        if product_info:
            # Check if product is in stock
            if not product_info.get('in_stock', False):
                await update.message.reply_text(
                    f"**❌ متاسفانه این محصول به اتمام رسیده است**\n\n"
                    f"**📦 {product_info['name']}**\n\n"
                    f"لطفاً بعداً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                    parse_mode='Markdown'
                )
            else:
                # Product is in stock, proceed normally
                save_product_to_db(product_info)
                context.user_data['current_product'] = product_info
                context.user_data['awaiting_quantity'] = True
                
                # Show stock quantity if available
                stock_msg = ""
                if product_info.get('manage_stock') and product_info.get('stock_quantity'):
                    stock_qty = product_info['stock_quantity']
                    if stock_qty < 50:  # Show warning if stock is low
                        stock_msg = f"\n**⚠️ فقط {stock_qty} عدد موجود است**"
                
                message = f"**✅ محصول پیدا شد!**\n\n**📦 {product_info['name']}**\n**💰 قیمت:** {product_info['price']:,.0f} تومان\n**📊 حداقل:** {product_info['min_quantity']} عدد{stock_msg}\n\n**❓ تعداد را وارد کنید:**"
                
                # Add back button
                keyboard = [[KeyboardButton("🔙 بازگشت به منو")]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text("**❌ محصول پیدا نشد.**", parse_mode='Markdown')
    else:
        keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(f"**👋 سلام {user.first_name}!**\n\n**به ربات فروش هوم پلاست خوش آمدید 🛒**\n\nبرای سفارش، از کانال دکمه «سفارش محصول» را بزنید.",
                                       reply_markup=reply_markup, parse_mode='Markdown')

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_new_quantity'):
        text = update.message.text.strip()
        if not text.isdigit():
            await update.message.reply_text("**❌ فقط عدد وارد کنید.**", parse_mode='Markdown')
            return
        
        new_quantity = int(text)
        product_id = context.user_data.get('editing_product_id')
        user_id = update.effective_user.id
        
        conn = get_db_connection()
        product_price = 0
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT price FROM products WHERE product_id = %s", (product_id,))
                    result = cursor.fetchone()
                    if result:
                        product_price = result['price']
            finally:
                conn.close()
        
        if product_price <= 30000:
            min_qty = 12
        elif 30000 < product_price <= 100000:
            min_qty = 6
        else:
            min_qty = 1
        
        if new_quantity < min_qty:
            await update.message.reply_text(f"**❌ حداقل {min_qty} عدد!**\n\nلطفاً تعداد بیشتری وارد کنید:", parse_mode='Markdown')
            return
        
        if update_cart_quantity(user_id, product_id, new_quantity):
            context.user_data['awaiting_new_quantity'] = False
            context.user_data.pop('editing_product_id', None)
            cart_items = get_user_cart(user_id)
            cart_text = format_cart(cart_items)
            keyboard = [
                [InlineKeyboardButton("➕ افزودن", callback_data="add_more"), InlineKeyboardButton("✏️ ویرایش", callback_data="edit_cart")],
                [InlineKeyboardButton("✅ تکمیل", callback_data="finish_order"), InlineKeyboardButton("❌ لغو", callback_data="cancel_order")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"**✅ تعداد بروز شد!**\n\n{cart_text}", reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    if not context.user_data.get('awaiting_quantity'):
        return
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("**❌ فقط عدد وارد کنید.**", parse_mode='Markdown')
        return
    
    quantity = int(text)
    product_info = context.user_data.get('current_product')
    if not product_info:
        await update.message.reply_text("**❌ خطا!**", parse_mode='Markdown')
        context.user_data.clear()
        return
    
    min_qty = product_info['min_quantity']
    if quantity < min_qty:
        await update.message.reply_text(f"**❌ حداقل {min_qty} عدد!**", parse_mode='Markdown')
        return
    
    # Check if there's enough stock (if stock management is enabled)
    if product_info.get('manage_stock') and product_info.get('stock_quantity'):
        available_stock = product_info['stock_quantity']
        if quantity > available_stock:
            await update.message.reply_text(
                f"**❌ موجودی کافی نیست!**\n\n"
                f"تعداد درخواستی: {quantity}\n"
                f"موجودی فعلی: {available_stock}\n\n"
                f"لطفاً تعداد کمتری وارد کنید.",
                parse_mode='Markdown'
            )
            return
    
    user_id = update.effective_user.id
    if add_to_cart(user_id, product_info['product_id'], quantity):
        context.user_data['awaiting_quantity'] = False
        cart_items = get_user_cart(user_id)
        cart_text = format_cart(cart_items)
        keyboard = [
            [InlineKeyboardButton("➕ افزودن", callback_data="add_more"), InlineKeyboardButton("✏️ ویرایش", callback_data="edit_cart")],
            [InlineKeyboardButton("✅ تکمیل", callback_data="finish_order"), InlineKeyboardButton("❌ لغو", callback_data="cancel_order")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"**✅ اضافه شد!**\n\n{cart_text}", reply_markup=reply_markup, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if query.data == "edit_name":
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_message(chat_id=user_id, text="**✏️ نام جدید خود را وارد کنید:**", parse_mode='Markdown')
        context.user_data['awaiting_name'] = True
        context.user_data['editing_profile'] = True
        return
    
    elif query.data == "edit_phone":
        try:
            await query.message.delete()
        except:
            pass
        keyboard = [[KeyboardButton("📱 ارسال شماره", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await context.bot.send_message(chat_id=user_id, text="**✏️ شماره جدید خود را وارد کنید:**\n(می‌توانید تایپ کنید یا از دکمه استفاده کنید)",
                                       reply_markup=reply_markup, parse_mode='Markdown')
        context.user_data['editing_phone'] = True
        context.user_data['awaiting_phone'] = True
        return
    
    elif query.data == "cancel_edit":
        try:
            await query.message.delete()
        except:
            pass
        keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await context.bot.send_message(chat_id=user_id, text="**✅ بازگشت به منو**", reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    if query.data == "add_more":
        await query.edit_message_text("**✅ برای افزودن محصول، به کانال مراجعه کنید.**", parse_mode='Markdown')
    elif query.data == "edit_cart":
        cart_items = get_user_cart(user_id)
        if not cart_items:
            await query.edit_message_text("**🛒 سبد خالی است.**", parse_mode='Markdown')
            return
        keyboard = []
        for item in cart_items:
            product_name = item.get('product_name') or f"محصول {item['product_id']}"
            keyboard.append([InlineKeyboardButton(f"✏️ {product_name}", callback_data=f"edit_{item['product_id']}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_cart")])
        await query.edit_message_text("**✏️ محصول مورد نظر را انتخاب کنید:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data.startswith("edit_"):
        product_id = query.data.replace("edit_", "")
        keyboard = [
            [InlineKeyboardButton("✏️ تغییر تعداد", callback_data=f"change_qty_{product_id}")],
            [InlineKeyboardButton("🗑 حذف محصول", callback_data=f"remove_{product_id}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="edit_cart")]
        ]
        await query.edit_message_text("**انتخاب کنید:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data.startswith("change_qty_"):
        product_id = query.data.replace("change_qty_", "")
        context.user_data['editing_product_id'] = product_id
        context.user_data['awaiting_new_quantity'] = True
        
        # Send a message with back button
        keyboard = [[KeyboardButton("🔙 بازگشت به سبد")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await query.edit_message_text("**✏️ تعداد جدید را وارد کنید:**", parse_mode='Markdown')
        await context.bot.send_message(
            chat_id=user_id, 
            text="برای لغو و بازگشت به سبد خرید، دکمه زیر را بزنید:",
            reply_markup=reply_markup
        )
    elif query.data.startswith("remove_"):
        product_id = query.data.replace("remove_", "")
        remove_from_cart(user_id, product_id)
        cart_items = get_user_cart(user_id)
        if cart_items:
            cart_text = format_cart(cart_items)
            keyboard = [
                [InlineKeyboardButton("➕ افزودن", callback_data="add_more"), InlineKeyboardButton("✏️ ویرایش", callback_data="edit_cart")],
                [InlineKeyboardButton("✅ تکمیل", callback_data="finish_order"), InlineKeyboardButton("❌ لغو", callback_data="cancel_order")]
            ]
            await query.edit_message_text(f"**✅ حذف شد!**\n\n{cart_text}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await query.edit_message_text("**🛒 سبد خالی شد.**", parse_mode='Markdown')
    elif query.data == "back_to_cart":
        cart_items = get_user_cart(user_id)
        cart_text = format_cart(cart_items)
        keyboard = [
            [InlineKeyboardButton("➕ افزودن", callback_data="add_more"), InlineKeyboardButton("✏️ ویرایش", callback_data="edit_cart")],
            [InlineKeyboardButton("✅ تکمیل", callback_data="finish_order"), InlineKeyboardButton("❌ لغو", callback_data="cancel_order")]
        ]
        await query.edit_message_text(cart_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == "cancel_order":
        clear_user_cart(user_id)
        await query.edit_message_text("**❌ لغو شد.**", parse_mode='Markdown')
    elif query.data == "finish_order":
        user_info = get_user_info(user_id)
        if user_info and user_info.get('phone_number'):
            cart_items = get_user_cart(user_id)
            if not cart_items:
                await query.edit_message_text("**❌ سبد خالی!**", parse_mode='Markdown')
                return
            order_id = create_order(user_id, cart_items)
            if order_id:
                clear_user_cart(user_id)
                cart_text = format_cart(cart_items)
                user_name = user_info.get('first_name', 'مشتری')
                phone = user_info.get('phone_number')
                confirmation = f"**✅ سفارش ثبت شد!**\n\n**📋 شماره: {order_id:04d}**\n**👤 {user_name}**\n\n{cart_text}\n\n**✅ برای ادمین ارسال شد.**\n**⏰ به زودی تماس می‌گیریم.**\n\n**🙏 متشکریم!**"
                await query.edit_message_text(confirmation, parse_mode='Markdown')
                admin_msg = f"**🔔 سفارش جدید!**\n\n**📋 #{order_id:04d}**\n**👤 {user_name}**\n**📱 {phone}**\n**🆔 {user_id}**\n\n{cart_text}"
                try:
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Error: {e}")
        else:
            await query.edit_message_text("**✅ لطفاً نام کامل خود را وارد کنید:**", parse_mode='Markdown')
            context.user_data['awaiting_name'] = True

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user_id = update.effective_user.id
    if contact:
        phone = contact.phone_number
        update_user_phone(user_id, phone)
        if context.user_data.get('editing_phone'):
            context.user_data.clear()
            keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("**✅ شماره شما بروز شد!**", reply_markup=reply_markup, parse_mode='Markdown')
            return
        if context.user_data.get('registering'):
            context.user_data.clear()
            keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("**✅ ثبت نام با موفقیت انجام شد!**\n\nاطلاعات شما ذخیره شد.", reply_markup=reply_markup, parse_mode='Markdown')
            return
        cart_items = get_user_cart(user_id)
        if not cart_items:
            keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("**❌ سبد خالی!**", reply_markup=reply_markup, parse_mode='Markdown')
            return
        order_id = create_order(user_id, cart_items)
        if order_id:
            clear_user_cart(user_id)
            cart_text = format_cart(cart_items)
            user_info = get_user_info(user_id)
            user_name = user_info.get('first_name', 'مشتری') if user_info else 'مشتری'
            confirmation = f"**✅ سفارش ثبت شد!**\n\n**📋 شماره: {order_id:04d}**\n**👤 {user_name}**\n\n{cart_text}\n\n**✅ برای ادمین ارسال شد.**\n**⏰ به زودی تماس می‌گیریم.**\n\n**🙏 متشکریم!**"
            keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(confirmation, reply_markup=reply_markup, parse_mode='Markdown')
            admin_msg = f"**🔔 سفارش جدید!**\n\n**📋 #{order_id:04d}**\n**👤 {user_name}**\n**📱 {phone}**\n**🆔 {user_id}**\n\n{cart_text}"
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error: {e}")
            context.user_data.clear()

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_name'):
        return
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("**❌ نام خیلی کوتاه است.**", parse_mode='Markdown')
        return
    user_id = update.effective_user.id
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET first_name = %s WHERE user_id = %s", (name, user_id))
            conn.commit()
        finally:
            conn.close()
    context.user_data['user_name'] = name
    context.user_data['awaiting_name'] = False
    if context.user_data.get('editing_profile'):
        context.user_data.clear()
        keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("**✅ نام شما بروز شد!**", reply_markup=reply_markup, parse_mode='Markdown')
        return
    context.user_data['awaiting_phone'] = True
    keyboard = [[KeyboardButton("📱 ارسال شماره", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(f"**✅ سلام {name}!**\n\n**شماره خود را ارسال کنید:**\n(می‌توانید شماره را تایپ کنید یا از دکمه استفاده کنید)", reply_markup=reply_markup, parse_mode='Markdown')

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    orders = get_user_orders(user_id)
    if not orders:
        await update.message.reply_text("**📋 هنوز سفارشی ندارید.**", parse_mode='Markdown')
        return
    text = "**🛒 سفارشات شما:**\n\n"
    for order in orders:
        emoji = {'pending': '⏳', 'confirmed': '✅', 'cancelled': '❌', 'completed': '✅'}.get(order['status'], '📦')
        text += f"{emoji} **#{order['order_id']:04d}**\n{order['created_at'].strftime('%Y/%m/%d')}\n{order['total_amount']:,.0f} تومان - {order['item_count']} محصول\n➖➖➖➖➖\n\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = get_user_info(user_id)
    if user_info and user_info.get('phone_number') and user_info.get('first_name'):
        keyboard = [
            [InlineKeyboardButton("✏️ ویرایش نام", callback_data="edit_name")],
            [InlineKeyboardButton("✏️ ویرایش شماره", callback_data="edit_phone")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="cancel_edit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"**✅ اطلاعات شما:**\n\n**👤 نام:** {user_info.get('first_name', '')}\n**📱 شماره:** {user_info.get('phone_number')}\n\nبرای ویرایش یکی از موارد را انتخاب کنید:",
            reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text("**📝 ثبت نام**\n\n**نام کامل خود را وارد کنید:**", parse_mode='Markdown')
        context.user_data['awaiting_name'] = True
        context.user_data['registering'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Check for back button first - this works in any state
    if text == "🔙 بازگشت به منو":
        context.user_data.clear()
        keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("**✅ بازگشت به منوی اصلی**", reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Check for back to cart button when editing quantity
    if text == "🔙 بازگشت به سبد":
        if context.user_data.get('awaiting_new_quantity'):
            context.user_data.clear()
            user_id = update.effective_user.id
            cart_items = get_user_cart(user_id)
            cart_text = format_cart(cart_items)
            keyboard = [
                [InlineKeyboardButton("➕ افزودن", callback_data="add_more"), InlineKeyboardButton("✏️ ویرایش", callback_data="edit_cart")],
                [InlineKeyboardButton("✅ تکمیل", callback_data="finish_order"), InlineKeyboardButton("❌ لغو", callback_data="cancel_order")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"**✅ بازگشت به سبد خرید**\n\n{cart_text}", reply_markup=reply_markup, parse_mode='Markdown')
            return
    
    # Check if user is in awaiting_quantity state and pressed a menu button
    if context.user_data.get('awaiting_quantity') and text in ["🛒 سفارشات من", "📝 ثبت نام", "📞 پشتیبانی"]:
        # Clear the state and process the menu button
        context.user_data.clear()
        keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("**✅ عملیات قبلی لغو شد.**", reply_markup=reply_markup, parse_mode='Markdown')
        # Now process the menu button
        if text == "🛒 سفارشات من":
            await show_orders(update, context)
            return
        elif text == "📝 ثبت نام":
            await register_user(update, context)
            return
        elif text == "📞 پشتیبانی":
            admin_username = ADMIN_USERNAME if ADMIN_USERNAME.startswith('@') else f'@{ADMIN_USERNAME}'
            await update.message.reply_text(
                f"برای تماس با پشتیبانی، روی لینک زیر کلیک کنید:\n\n{admin_username}"
            )
            return
    
    if context.user_data.get('awaiting_new_quantity'):
        await handle_quantity(update, context)
        return
    if context.user_data.get('awaiting_name'):
        await handle_name(update, context)
        return
    if context.user_data.get('awaiting_quantity'):
        await handle_quantity(update, context)
        return
    if context.user_data.get('awaiting_phone') or context.user_data.get('registering') or context.user_data.get('editing_phone'):
        phone = text.strip()
        phone = convert_persian_to_english(phone)
        if phone.startswith('09') and len(phone) == 11 and phone.isdigit():
            user_id = update.effective_user.id
            update_user_phone(user_id, phone)
            if context.user_data.get('editing_phone'):
                context.user_data.clear()
                keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text("**✅ شماره شما بروز شد!**", reply_markup=reply_markup, parse_mode='Markdown')
                return
            if context.user_data.get('registering'):
                context.user_data.clear()
                keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text("**✅ ثبت نام با موفقیت انجام شد!**\n\nاطلاعات شما ذخیره شد.", reply_markup=reply_markup, parse_mode='Markdown')
                return
            cart_items = get_user_cart(user_id)
            if not cart_items:
                keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text("**❌ سبد خالی!**", reply_markup=reply_markup, parse_mode='Markdown')
                return
            order_id = create_order(user_id, cart_items)
            if order_id:
                clear_user_cart(user_id)
                cart_text = format_cart(cart_items)
                user_info = get_user_info(user_id)
                user_name = user_info.get('first_name', 'مشتری') if user_info else 'مشتری'
                confirmation = f"**✅ سفارش ثبت شد!**\n\n**📋 شماره: {order_id:04d}**\n**👤 {user_name}**\n\n{cart_text}\n\n**✅ برای ادمین ارسال شد.**\n**⏰ به زودی تماس می‌گیریم.**\n\n**🙏 متشکریم!**"
                keyboard = [[KeyboardButton("🛒 سفارشات من"), KeyboardButton("📝 ثبت نام")], [KeyboardButton("📞 پشتیبانی")]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(confirmation, reply_markup=reply_markup, parse_mode='Markdown')
                admin_msg = f"**🔔 سفارش جدید!**\n\n**📋 #{order_id:04d}**\n**👤 {user_name}**\n**📱 {phone}**\n**🆔 {user_id}**\n\n{cart_text}"
                try:
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Error: {e}")
                context.user_data.clear()
            return
        else:
            await update.message.reply_text("**❌ شماره نامعتبر است!**\n\nشماره باید با 09 شروع شود و 11 رقم باشد.\n\nمثال: 09123456789", parse_mode='Markdown')
            return
    if text == "🛒 سفارشات من":
        await show_orders(update, context)
    elif text == "📝 ثبت نام":
        await register_user(update, context)
    elif text == "📞 پشتیبانی":
        # Format admin username with @ if not already present
        admin_username = ADMIN_USERNAME if ADMIN_USERNAME.startswith('@') else f'@{ADMIN_USERNAME}'
        # Send without parse_mode to avoid Markdown parsing issues with @username
        await update.message.reply_text(
            f"برای تماس با پشتیبانی، روی لینک زیر کلیک کنید:\n\n{admin_username}"
        )
    else:
        await update.message.reply_text("**لطفاً از منو یا کانال انتخاب کنید.**", parse_mode='Markdown')

def main():
    logger.info("Starting bot...")
    application = Application.builder().token(BOT_TOKEN).build()
    from telegram import BotCommand
    commands = [BotCommand("start", "شروع و منوی اصلی")]
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.bot.set_my_commands(commands))
    logger.info("Bot started!")
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
