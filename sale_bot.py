# -*- coding: utf-8 -*-
"""
Hom Plast Telegram Sales Bot - Refactored Version
Version: 1.0.2
Last Updated: 2025-01-27
Description: Customer ordering bot for Hom Plast channel - Refactored
"""

__version__ = "1.0.2"
__author__ = "Hom Plast Dev Team"
__last_updated__ = "2025-01-27"

# Import extracted modules
from config.settings import *
from config.database import *
from utils.validators import InputValidator
# Rate limiting temporarily removed to avoid issues
# from utils.rate_limiter import RateLimiter, user_action_store
import time

# Import Telegram libraries
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Import WooCommerce function
import requests
from requests.auth import HTTPBasicAuth

# Import Persian date library
try:
    import jdatetime
    PERSIAN_DATE_AVAILABLE = True
except ImportError:
    PERSIAN_DATE_AVAILABLE = False
    logger.warning("jdatetime library not installed. Install with: pip install jdatetime")
    from datetime import datetime as fallback_datetime

logger.info(f"Starting Hom Plast Sales Bot v{__version__}")

def convert_persian_to_english(text):
    """Convert Persian/Arabic digits to English digits"""
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits + arabic_digits, english_digits * 2)
    return text.translate(translation_table)

def format_persian_date(dt):
    """Convert Gregorian date to Persian (Jalali) date string"""
    if not PERSIAN_DATE_AVAILABLE:
        # Fallback to Gregorian if jdatetime is not available
        return dt.strftime('%Y/%m/%d')
    
    try:
        # Import datetime if needed
        from datetime import datetime
        
        # Convert datetime to Persian date
        if isinstance(dt, str):
            # If it's a string, try multiple formats to parse it
            try:
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    dt = datetime.strptime(dt, '%Y-%m-%d')
                except ValueError:
                    logger.error(f"Could not parse date string: {dt}")
                    return str(dt)
        elif hasattr(dt, 'strftime'):
            # Already a datetime object, use it
            pass
        else:
            logger.error(f"Invalid date format: {type(dt)}")
            return str(dt)
        
        persian_date = jdatetime.datetime.fromgregorian(datetime=dt)
        # Format as YYYY/MM/DD
        return persian_date.strftime('%Y/%m/%d')
    except Exception as e:
        logger.error(f"Error converting date to Persian: {e}")
        # Fallback to Gregorian on error
        if hasattr(dt, 'strftime'):
            return dt.strftime('%Y/%m/%d')
        else:
            return str(dt)

def create_back_to_post_button(context):
    """Helper function to create back to post button"""
    if context.user_data.get('source_message_id') and context.user_data.get('source_channel'):
        msg_id = context.user_data['source_message_id']
        channel = context.user_data['source_channel']
        return InlineKeyboardButton("🛒 ادامه خرید", url=f"https://t.me/{channel}/{msg_id}")
    else:
        # Fallback: direct link to channel when no specific post
        return InlineKeyboardButton("🛒 ادامه خرید", url="https://t.me/hom_plast")

def fetch_product_from_woocommerce(sku: str):
    """Fetch product from WooCommerce API"""
    try:
        url = f"{WC_URL}/wp-json/wc/v3/products"
        auth = HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
        response = requests.get(url, params={'sku': sku}, auth=auth, timeout=5)

        if response.status_code == 200:
            products = response.json()
            if products and len(products) > 0:
                product = products[0]
                name = product.get('name', f'Product {sku}')
                price = float(product.get('regular_price', 0))

                stock_status = product.get('stock_status', 'outofstock')
                stock_quantity = product.get('stock_quantity', 0)
                manage_stock = product.get('manage_stock', False)
                in_stock = stock_status == 'instock'

                if price <= 30000:
                    min_quantity = 12
                elif 30000 < price <= 100000:
                    min_quantity = 6
                else:
                    min_quantity = 1

                # Get product images
                images = []
                if product.get('images'):
                    for img in product.get('images', []):
                        if img.get('src'):
                            images.append(img.get('src'))
                
                logger.info(f"Product: {name}, Price: {price}, Min: {min_quantity}, Stock: {stock_status}, Qty: {stock_quantity}, Images: {len(images)}")
                return {
                    'product_id': sku,
                    'name': name,
                    'price': price,
                    'min_quantity': min_quantity,
                    'in_stock': in_stock,
                    'stock_quantity': stock_quantity,
                    'manage_stock': manage_stock,
                    'images': images  # List of image URLs
                }
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def format_cart(cart_items):
    """Format cart items for display"""
    if not cart_items:
        return "🛒 سبد خرید خالی است."
    text = ""
    total = 0
    for idx, item in enumerate(cart_items, 1):
        product_name = item.get('product_name') or f"محصول {item['product_id']}"
        product_id = item.get('product_id', 'نامشخص')
        price = item.get('price') or 0
        quantity = item['quantity']
        subtotal = price * quantity
        total += subtotal
        # Use single asterisk for bold (works with Persian text)
        text += f"*{idx}- {product_name}*\nشناسه محصول: {product_id}\n{quantity} x {price:,.0f} = {subtotal:,.0f}\n➖➖➖➖➖➖➖\n\n"
    
    # Use single asterisk for bold total line
    text += f"💰 *مجموع: {total:,.0f} تومان*"
    return text

def create_cart_keyboard(context):
    """Helper function to create cart keyboard with dynamic back button"""
    back_button = create_back_to_post_button(context)
    keyboard = [
        [back_button, InlineKeyboardButton("✏️ ویرایش سبد خرید", callback_data="edit_cart")],
        [InlineKeyboardButton("✅ تکمیل سفارش", callback_data="finish_order"), InlineKeyboardButton("❌ لغو سبد خرید", callback_data="cancel_order")]
    ]
    return keyboard

def create_main_menu_keyboard():
    """Helper function to create main menu keyboard"""
    keyboard = [
        [KeyboardButton("🛒 مشاهده سبد خرید"), KeyboardButton("✍️ ثبت نام")],
        [KeyboardButton("📦 سفارشات من"), KeyboardButton("☎️ پشتیبانی")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_channel_button():
    """Helper function to create channel inline button"""
    keyboard = [[InlineKeyboardButton("📱 بازگشت به کانال", url="https://t.me/hom_plast")]]
    return InlineKeyboardMarkup(keyboard)

def calculate_effective_quantity_limits(product_info, user_id, exclude_product_id=None):
    """
    Calculate effective min and max quantities based on product info and cart.
    Returns: (effective_min, effective_max, remaining_stock, current_cart_qty)
    """
    try:
        # Calculate original minimum based on price
        product_price = float(product_info.get('price', 0))
        if product_price <= 30000:
            original_min = 12
        elif 30000 < product_price <= 100000:
            original_min = 6
        else:
            original_min = 1
        
        # Get current quantity in cart for this product
        current_cart_qty = 0
        cart_items = get_user_cart(user_id)
        other_cart_qty = 0
        
        if cart_items:
            for item in cart_items:
                if item and isinstance(item, dict):
                    item_product_id = str(item.get('product_id', ''))
                    product_id = str(product_info.get('product_id', ''))
                    if item_product_id == product_id:
                        # Skip the item being edited if exclude_product_id is provided
                        if exclude_product_id and item_product_id == str(exclude_product_id):
                            continue  # Skip the item being edited
                        current_cart_qty = item.get('quantity', 0)
                        other_cart_qty += item.get('quantity', 0)
        
        # Calculate effective min and max based on stock
        if product_info.get('manage_stock') and product_info.get('stock_quantity'):
            available_stock = int(product_info.get('stock_quantity', 0))
            remaining_stock = available_stock - other_cart_qty
            
            # Dynamic minimum: If remaining stock < original minimum, adjust to 1
            if remaining_stock < original_min:
                effective_min = 1
            else:
                effective_min = original_min
            
            # Maximum is remaining stock
            effective_max = max(1, remaining_stock)  # At least 1 if stock available
            
            return effective_min, effective_max, remaining_stock, current_cart_qty
        else:
            # No stock management - just use original minimum
            effective_min = original_min
            effective_max = 999999  # No limit
            return effective_min, effective_max, None, current_cart_qty
    except Exception as e:
        logger.error(f"Error calculating effective quantity limits: {e}", exc_info=True)
        # Return safe defaults
        return 1, 999999, None, 0

def create_quantity_keyboard(product_id, current_quantity, effective_min, effective_max, image_index=0, total_images=0):
    """Create inline keyboard with quantity buttons and optional image gallery navigation"""
    # Ensure product_id is a string
    product_id = str(product_id) if product_id else ""
    
    # Ensure current_quantity is an integer
    current_quantity = int(current_quantity) if current_quantity else 1
    effective_min = int(effective_min) if effective_min else 1
    effective_max = int(effective_max) if effective_max else 999999
    
    # Disable decrease button if at minimum
    decrease_disabled = current_quantity <= effective_min
    # Disable increase button if at maximum
    increase_disabled = current_quantity >= effective_max
    
    keyboard = []
    
    # Add image gallery navigation if multiple images exist
    if total_images > 1:
        prev_disabled = image_index <= 0
        next_disabled = image_index >= total_images - 1
        gallery_row = []
        if not prev_disabled:
            gallery_row.append(InlineKeyboardButton("◀️", callback_data=f"img_prev_{product_id}_{image_index}"))
        gallery_row.append(InlineKeyboardButton(f"🖼️ {image_index + 1}/{total_images}", callback_data="img_info"))
        if not next_disabled:
            gallery_row.append(InlineKeyboardButton("▶️", callback_data=f"img_next_{product_id}_{image_index}"))
        if gallery_row:
            keyboard.append(gallery_row)
    
    # Quantity buttons
    keyboard.append([
        InlineKeyboardButton(
            "➖",
            callback_data=f"qty_dec_{product_id}" if not decrease_disabled else "qty_min_reached"
        ),
        InlineKeyboardButton(
            str(current_quantity),
            callback_data="qty_display"
        ),
        InlineKeyboardButton(
            "➕",
            callback_data=f"qty_inc_{product_id}" if not increase_disabled else "qty_max_reached"
        )
    ])
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("🛒 افزودن به سبد", callback_data=f"qty_add_cart_{product_id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("⌨️ تایپ تعداد", callback_data=f"qty_type_{product_id}"),
        InlineKeyboardButton("❌ انصراف", callback_data="cancel_product_add")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def format_product_with_quantity(product_info, current_quantity, effective_min, effective_max, remaining_stock=None):
    """Format product message with current quantity"""
    try:
        product_name = product_info.get('name', 'محصول')
        product_id = product_info.get('product_id', 'نامشخص')
        product_price = float(product_info.get('price', 0))
        
        message = (
            f"*✅ محصول مورد نظر انتخاب شد!*\n\n"
            f"*📦 {product_name}*\n"
            f"*🆔 شناسه محصول:* {product_id}\n"
            f"*💰 قیمت:* {product_price:,.0f} تومان\n"
            f"*📊 حداقل:* {effective_min} عدد\n\n"
            f"*🔢 تعداد انتخاب شده: {current_quantity}*\n\n"
            f"از دکمه‌های زیر برای تغییر تعداد استفاده کنید یا تعداد را تایپ کنید:"
        )
        return message
    except Exception as e:
        logger.error(f"Error formatting product message: {e}", exc_info=True)
        # Return a simple fallback message
        return (
            f"*✅ محصول مورد نظر انتخاب شد!*\n\n"
            f"*📦 {product_info.get('name', 'محصول')}*\n"
            f"*🔢 تعداد: {current_quantity}*\n\n"
            f"از دکمه‌های زیر برای تغییر تعداد استفاده کنید:"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with validation"""
    user = update.effective_user

    # Save user info
    save_user(user.id, user.username, user.first_name, user.last_name)

    # Log for debugging
    logger.info(f"Start command called with args: {context.args}")

    # If there are arguments (like product selection), process them first
    # and return early to avoid showing welcome message
    if context.args:
        arg = context.args[0]

        if arg == 'myorders':
            await show_orders(update, context)
            return

        elif arg.startswith('product_'):
            # Parse: product_SKU_mMSGID_cCHANNEL
            message_id = None
            channel_ref = None
            product_sku = ''

            # Find the positions of _m and _c markers
            m_index = arg.find('_m')
            c_index = arg.find('_c')

            if m_index > 0 and c_index > m_index:
                # Extract SKU (everything between 'product_' and '_m')
                product_sku = arg[8:m_index]  # 8 = len('product_')

                # Extract message_id (between '_m' and '_c')
                message_id = arg[m_index+2:c_index]

                # Extract channel (everything after '_c')
                channel_ref = arg[c_index+2:]
            else:
                # Fallback: old format without message_id
                product_sku = arg.replace('product_', '').split('_')[0]

            # Store in user context for creating back button later
            if message_id and channel_ref:
                context.user_data['source_message_id'] = message_id
                context.user_data['source_channel'] = channel_ref
                logger.info(f"User came from channel {channel_ref}, message {message_id}")

            # Validate SKU
            is_valid, error_msg, clean_sku = InputValidator.validate_sku(product_sku)
            if not is_valid:
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=f"**❌ {error_msg}**",
                    parse_mode='Markdown'
                )
                return

            loading_msg = await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="**⏳ لطفاً صبر کنید...**",
                parse_mode='Markdown'
            )
            
            try:
                # Try to fetch product from WooCommerce
                try:
                    product_info = fetch_product_from_woocommerce(clean_sku)
                except requests.exceptions.Timeout:
                    raise TimeoutError("WooCommerce API timeout")
                except Exception as e:
                    logger.error(f"Error fetching product {clean_sku} from WooCommerce: {e}")
                    raise

                # Delete loading message after fetch (whether success or failure)
                try:
                    await loading_msg.delete()
                except:
                    pass

                # Process product info
                if product_info:
                    if not product_info.get('in_stock', False):
                        back_button = create_back_to_post_button(context)
                        keyboard = InlineKeyboardMarkup([[back_button]])
                        await context.bot.send_message(
                            chat_id=update.effective_user.id,
                            text=f"**❌ متاسفانه این محصول به اتمام رسیده است**\n\n"
                            f"**📦 {product_info['name']}**\n\n"
                            f"لطفاً بعداً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                            reply_markup=keyboard,
                            parse_mode='Markdown'
                        )
                    else:
                        # Try to save product to database
                        try:
                            save_product_to_db(product_info)
                        except Exception as e:
                            logger.error(f"Error saving product to database: {e}")
                            # Continue anyway - database save failure shouldn't block user

                        context.user_data['current_product'] = product_info
                        context.user_data['awaiting_quantity'] = True
                        
                        try:
                            # Calculate effective min/max quantities
                            user_id = update.effective_user.id
                            effective_min, effective_max, remaining_stock, current_cart_qty = calculate_effective_quantity_limits(
                                product_info, user_id
                            )
                            
                            # Initialize quantity to effective minimum (or 1 if dynamic min applies)
                            initial_quantity = max(effective_min, 1)
                            context.user_data['current_quantity'] = initial_quantity
                            context.user_data['effective_min'] = effective_min
                            context.user_data['effective_max'] = effective_max

                            # Format product message with quantity
                            message = format_product_with_quantity(
                                product_info, initial_quantity, effective_min, effective_max, remaining_stock
                            )

                            # Get product images
                            images = product_info.get('images', [])
                            context.user_data['product_images'] = images
                            context.user_data['current_image_index'] = 0
                            
                            # Create quantity keyboard with image gallery if multiple images
                            keyboard = create_quantity_keyboard(
                                product_info['product_id'], 
                                initial_quantity, 
                                effective_min, 
                                effective_max,
                                image_index=0,
                                total_images=len(images)
                            )
                            
                            # Send product with image if available
                            if images and len(images) > 0:
                                await context.bot.send_photo(
                                    chat_id=update.effective_user.id,
                                    photo=images[0],
                                    caption=message,
                                    reply_markup=keyboard,
                                    parse_mode='Markdown'
                                )
                            else:
                                await context.bot.send_message(
                                    chat_id=update.effective_user.id,
                                    text=message,
                                    reply_markup=keyboard,
                                    parse_mode='Markdown'
                                )
                        except Exception as e:
                            logger.error(f"Error displaying product with quantity buttons: {e}", exc_info=True)
                            # Fallback to original text input method
                            message = (
                                f"*✅ محصول مورد نظر انتخاب شد!*\n\n"
                                f"*📦 {product_info['name']}*\n"
                                f"*🆔 شناسه محصول:* {product_info['product_id']}\n"
                                f"*💰 قیمت:* {product_info['price']:,.0f} تومان\n"
                                f"*📊 حداقل:* {product_info['min_quantity']} عدد\n\n"
                                f"*❓ لطفاً تعداد مورد نظر را در قسمت پیام وارد کنید!*"
                            )

                            cancel_button = InlineKeyboardButton("❌ انصراف", callback_data="cancel_product_add")
                            keyboard = InlineKeyboardMarkup([[cancel_button]])
                            await context.bot.send_message(
                                chat_id=update.effective_user.id,
                                text=message,
                                reply_markup=keyboard,
                                parse_mode='Markdown'
                            )
                else:
                    back_button = create_back_to_post_button(context)
                    keyboard = InlineKeyboardMarkup([[back_button]])
                    await context.bot.send_message(
                        chat_id=update.effective_user.id,
                        text="**❌ محصول پیدا نشد.**\n\n"
                        "لطفاً مطمئن شوید که کد محصول صحیح است.",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                    
            except TimeoutError:
                # Handle timeout specifically
                try:
                    await loading_msg.delete()
                except:
                    pass
                back_button = create_back_to_post_button(context)
                keyboard = InlineKeyboardMarkup([[back_button]])
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="**⏰ زمان اتصال به سرور به پایان رسید.**\n\n"
                    "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            except Exception as e:
                # Handle any other error (database, message sending, etc.)
                logger.error(f"Unexpected error processing product {clean_sku}: {e}", exc_info=True)
                try:
                    await loading_msg.delete()
                except:
                    pass
                back_button = create_back_to_post_button(context)
                keyboard = InlineKeyboardMarkup([[back_button]])
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text="**❌ خطایی رخ داد.**\n\n"
                    "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            return

    # Only show welcome message if no arguments (not a product selection)
    # This prevents showing welcome message when user clicks product from channel
    if not context.args:
        reply_markup = create_main_menu_keyboard()
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f"**👋 سلام {user.first_name}!**\n\n"
            f"**به ربات فروش هوم پلاست خوش آمدید 🛒**\n\n"
            f"برای سفارش، از کانال دکمه «سفارش محصول» را بزنید.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        # Always show channel button
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="**📱 بازگشت به کانال:**",
            reply_markup=create_channel_button(),
            parse_mode='Markdown'
        )

async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity input with validation"""
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    
    if context.user_data.get('awaiting_new_quantity'):
        # Validate quantity input (format only, stock check comes later)
        is_valid, error_msg, clean_quantity = InputValidator.validate_quantity(text, min_qty=1, max_qty=999999)
        if not is_valid:
            await update.message.reply_text(f"**❌ {error_msg}**", parse_mode='Markdown')
            return

        product_id = context.user_data.get('editing_product_id')
        user_id = update.effective_user.id

        # Get product info from WooCommerce to check stock
        try:
            product_info = fetch_product_from_woocommerce(product_id)
        except Exception as e:
            logger.error(f"Error fetching product {product_id} for quantity update: {e}")
            await update.message.reply_text("**❌ خطا در دریافت اطلاعات محصول.**", parse_mode='Markdown')
            return
        
        if not product_info:
            await update.message.reply_text("**❌ محصول پیدا نشد.**", parse_mode='Markdown')
            return

        # Calculate minimum based on price
        product_price = product_info['price']
        if product_price <= 30000:
            original_min = 12
        elif 30000 < product_price <= 100000:
            original_min = 6
        else:
            original_min = 1

        # Check stock and apply dynamic minimum
        if product_info.get('manage_stock') and product_info.get('stock_quantity'):
            available_stock = product_info['stock_quantity']

            # Get OTHER items in cart (excluding the one being edited)
            cart_items = get_user_cart(user_id)
            other_cart_qty = 0
            for item in cart_items:
                if str(item['product_id']) == str(product_id):
                    continue  # Skip the item being edited
                if str(item['product_id']) == str(product_info['product_id']):
                    other_cart_qty += item['quantity']

            remaining_stock = available_stock - other_cart_qty

            # Dynamic minimum: If remaining stock < original minimum, adjust to 1
            if remaining_stock < original_min:
                effective_min = 1
            else:
                effective_min = original_min

            # Check minimum
            if clean_quantity < effective_min:
                await update.message.reply_text(
                    f"**❌ حداقل {effective_min} عدد!**\n\nلطفاً تعداد بیشتری وارد کنید:",
                    parse_mode='Markdown'
                )
                return

            # Check if new quantity exceeds available stock
            if clean_quantity > remaining_stock:
                await update.message.reply_text(
                    f"**❌ موجودی کافی نیست!**\n\n"
                    f"**✅ حداکثر می‌توانید {remaining_stock} عدد انتخاب کنید.**\n\n"
                    f"لطفاً تعداد کمتری وارد کنید:",
                    parse_mode='Markdown'
                )
                return
        else:
            # No stock management - just check minimum
            if clean_quantity < original_min:
                await update.message.reply_text(
                    f"**❌ حداقل {original_min} عدد!**\n\nلطفاً تعداد بیشتری وارد کنید:",
                    parse_mode='Markdown'
                )
                return

        if update_cart_quantity(user_id, product_id, clean_quantity):
            context.user_data['awaiting_new_quantity'] = False
            context.user_data.pop('editing_product_id', None)
            cart_items = get_user_cart(user_id)
            cart_text = format_cart(cart_items)

            keyboard = create_cart_keyboard(context)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"*✅ تعداد بروز شد!*\n\n{cart_text}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        return

    if not context.user_data.get('awaiting_quantity'):
        return
    
    # Check if user is in typing mode (from quantity buttons)
    is_typing_mode = context.user_data.get('awaiting_quantity_typing', False)
    
    # Validate quantity input (format only, stock check comes later)
    is_valid, error_msg, clean_quantity = InputValidator.validate_quantity(text, min_qty=1, max_qty=999999)
    if not is_valid:
        await update.message.reply_text(f"**❌ {error_msg}**", parse_mode='Markdown')
        return

    product_info = context.user_data.get('current_product')
    if not product_info:
        await update.message.reply_text("**❌ خطا!**", parse_mode='Markdown')
        context.user_data.clear()
        return

    user_id = update.effective_user.id
    
    # Calculate effective min/max using the helper function
    effective_min, effective_max, remaining_stock, current_cart_qty = calculate_effective_quantity_limits(
        product_info, user_id
    )
    
    # Check minimum quantity
    if clean_quantity < effective_min:
        await update.message.reply_text(
            f"**❌ حداقل {effective_min} عدد!**\n\nلطفاً تعداد بیشتری وارد کنید:",
            parse_mode='Markdown'
        )
        return
    
    # Check maximum quantity (if stock managed)
    if effective_max != 999999 and clean_quantity > effective_max:
        await update.message.reply_text(
            f"**❌ موجودی کافی نیست!**\n\n"
            f"**✅ حداکثر می‌توانید {effective_max} عدد انتخاب کنید.**\n\n"
            f"لطفاً تعداد کمتری وارد کنید:",
            parse_mode='Markdown'
        )
        return

    # If in typing mode from quantity buttons, update the quantity display
    if is_typing_mode:
        context.user_data['current_quantity'] = clean_quantity
        context.user_data['effective_min'] = effective_min
        context.user_data['effective_max'] = effective_max
        
        # Get current image index
        current_image_index = context.user_data.get('current_image_index', 0)
        images = context.user_data.get('product_images', [])
        
        # Show updated product with quantity buttons
        message = format_product_with_quantity(
            product_info, clean_quantity, effective_min, effective_max, remaining_stock
        )
        keyboard = create_quantity_keyboard(
            product_info['product_id'], clean_quantity, effective_min, effective_max,
            image_index=current_image_index,
            total_images=len(images)
        )
        
        # Send with image if available, otherwise text
        if images and len(images) > 0:
            await update.message.reply_photo(
                photo=images[current_image_index],
                caption=message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')
        context.user_data['awaiting_quantity_typing'] = False
        return

    # Try to add to cart (original flow for direct typing)
    if add_to_cart(user_id, product_info['product_id'], clean_quantity):
        context.user_data['awaiting_quantity'] = False
        cart_items = get_user_cart(user_id)
        cart_text = format_cart(cart_items)

        keyboard = create_cart_keyboard(context)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"*✅ اضافه شد!*\n\n{cart_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "edit_name":
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=user_id,
            text="**✏️ نام جدید خود را وارد کنید:**",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_name'] = True
        context.user_data['editing_profile'] = True
        return

    elif query.data == "edit_phone":
        try:
            await query.message.delete()
        except Exception:
            pass
        keyboard = [[KeyboardButton("📱 ارسال شماره", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await context.bot.send_message(
            chat_id=user_id,
            text="**✏️ شماره جدید خود را وارد کنید:**\n(می‌توانید تایپ کنید یا از دکمه استفاده کنید)",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        context.user_data['editing_phone'] = True
        context.user_data['awaiting_phone'] = True
        return

    elif query.data == "cancel_edit":
        try:
            await query.message.delete()
        except Exception:
            pass
        reply_markup = create_main_menu_keyboard()
        await context.bot.send_message(
            chat_id=user_id,
            text="**✅ بازگشت به منو**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    if query.data == "add_more":
        await query.edit_message_text(
            "**✅ برای افزودن محصول، به کانال مراجعه کنید.**",
            parse_mode='Markdown'
        )
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
        await query.edit_message_text(
            "**✏️ محصول مورد نظر را انتخاب کنید:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
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
            keyboard = create_cart_keyboard(context)
            await query.edit_message_text(
                f"*✅ حذف شد!*\n\n{cart_text}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            # Cart is now empty → clear inline keyboard and show menus
            try:
                await query.edit_message_text("*🛒 سبد خالی شد.*", reply_markup=None, parse_mode='Markdown')
            except Exception:
                pass
            await query.message.reply_text("*📱 بازگشت به کانال:*", reply_markup=create_channel_button(), parse_mode='Markdown')
            reply_markup = create_main_menu_keyboard()
            await query.message.reply_text("*منوی اصلی:*", reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "back_to_cart":
        cart_items = get_user_cart(user_id)
        if not cart_items:
            # Cart is empty: clear inline keyboard and restore menus
            try:
                await query.edit_message_text("*🛒 سبد خالی شد.*", reply_markup=None, parse_mode='Markdown')
            except Exception:
                pass
            await query.message.reply_text("*📱 بازگشت به کانال:*", reply_markup=create_channel_button(), parse_mode='Markdown')
            reply_markup = create_main_menu_keyboard()
            await query.message.reply_text("*منوی اصلی:*", reply_markup=reply_markup, parse_mode='Markdown')
        else:
            cart_text = format_cart(cart_items)
            keyboard = create_cart_keyboard(context)
            await query.edit_message_text(cart_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == "cancel_product_add":
        # Cancel product addition - same pattern as cart cancellation
        context.user_data.clear()  # Clear all pending states including awaiting_quantity
        
        # Check if message is a photo or text
        try:
            if query.message.photo:
                # It's a photo message - edit caption
                await query.edit_message_caption(
                    caption="*❌ افزودن محصول لغو شد.*",
                    reply_markup=None,
                    parse_mode='Markdown'
                )
            else:
                # It's a text message
                await query.edit_message_text("*❌ افزودن محصول لغو شد.*", reply_markup=None, parse_mode='Markdown')
        except Exception as e:
            # If editing fails, delete and send new message
            try:
                await query.message.delete()
            except:
                pass
            await query.message.reply_text("*❌ افزودن محصول لغو شد.*", parse_mode='Markdown')
        
        await query.message.reply_text("*📱 بازگشت به کانال:*", reply_markup=create_channel_button(), parse_mode='Markdown')
        # Restore main menu
        reply_markup = create_main_menu_keyboard()
        await query.message.reply_text("*منوی اصلی:*", reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data.startswith("qty_dec_"):
        # Decrease quantity
        product_id = query.data.replace("qty_dec_", "")
        product_info = context.user_data.get('current_product')
        if not product_info or str(product_info['product_id']) != str(product_id):
            await query.answer("❌ خطا در دریافت اطلاعات محصول", show_alert=True)
            return
        
        current_quantity = context.user_data.get('current_quantity', 1)
        effective_min = context.user_data.get('effective_min', 1)
        effective_max = context.user_data.get('effective_max', 999999)
        
        # Decrease quantity
        new_quantity = max(effective_min, current_quantity - 1)
        context.user_data['current_quantity'] = new_quantity
        
        # Recalculate limits (in case stock changed)
        user_id = update.effective_user.id
        effective_min, effective_max, remaining_stock, _ = calculate_effective_quantity_limits(
            product_info, user_id
        )
        context.user_data['effective_min'] = effective_min
        context.user_data['effective_max'] = effective_max
        
        # Update message
        message = format_product_with_quantity(
            product_info, new_quantity, effective_min, effective_max, remaining_stock
        )
        keyboard = create_quantity_keyboard(product_id, new_quantity, effective_min, effective_max)
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()
    elif query.data.startswith("qty_inc_"):
        # Increase quantity
        product_id = query.data.replace("qty_inc_", "")
        product_info = context.user_data.get('current_product')
        if not product_info or str(product_info['product_id']) != str(product_id):
            await query.answer("❌ خطا در دریافت اطلاعات محصول", show_alert=True)
            return
        
        current_quantity = context.user_data.get('current_quantity', 1)
        effective_min = context.user_data.get('effective_min', 1)
        effective_max = context.user_data.get('effective_max', 999999)
        
        # Increase quantity
        new_quantity = min(effective_max, current_quantity + 1)
        context.user_data['current_quantity'] = new_quantity
        
        # Recalculate limits (in case stock changed)
        user_id = update.effective_user.id
        effective_min, effective_max, remaining_stock, _ = calculate_effective_quantity_limits(
            product_info, user_id
        )
        context.user_data['effective_min'] = effective_min
        context.user_data['effective_max'] = effective_max
        
        # Get current image index
        current_image_index = context.user_data.get('current_image_index', 0)
        images = context.user_data.get('product_images', [])
        
        # Update message
        message = format_product_with_quantity(
            product_info, new_quantity, effective_min, effective_max, remaining_stock
        )
        keyboard = create_quantity_keyboard(
            product_id, new_quantity, effective_min, effective_max,
            image_index=current_image_index,
            total_images=len(images)
        )
        
        # Update photo if images exist, otherwise update text
        if images and len(images) > 0:
            await query.edit_message_caption(
                caption=message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer()
    elif query.data.startswith("img_prev_"):
        # Navigate to previous image
        # Format: img_prev_{product_id}_{index}
        data = query.data.replace("img_prev_", "")
        # Find last underscore (separates product_id from index)
        last_underscore = data.rfind("_")
        if last_underscore > 0:
            product_id = data[:last_underscore]
            current_index = int(data[last_underscore + 1:])
            
            product_info = context.user_data.get('current_product')
            if not product_info or str(product_info['product_id']) != str(product_id):
                await query.answer("❌ خطا در دریافت اطلاعات محصول", show_alert=True)
                return
            
            images = context.user_data.get('product_images', [])
            if not images or len(images) == 0:
                await query.answer("⚠️ تصویری موجود نیست", show_alert=True)
                return
            
            # Go to previous image
            new_index = max(0, current_index - 1)
            context.user_data['current_image_index'] = new_index
            
            # Get current quantity and limits
            current_quantity = context.user_data.get('current_quantity', 1)
            effective_min = context.user_data.get('effective_min', 1)
            effective_max = context.user_data.get('effective_max', 999999)
            user_id = update.effective_user.id
            _, _, remaining_stock, _ = calculate_effective_quantity_limits(product_info, user_id)
            
            # Format message
            message = format_product_with_quantity(
                product_info, current_quantity, effective_min, effective_max, remaining_stock
            )
            
            # Create keyboard
            keyboard = create_quantity_keyboard(
                product_id, current_quantity, effective_min, effective_max,
                image_index=new_index,
                total_images=len(images)
            )
            
            # Update photo
            await query.edit_message_media(
                media=InputMediaPhoto(media=images[new_index], caption=message, parse_mode='Markdown'),
                reply_markup=keyboard
            )
            await query.answer()
    elif query.data.startswith("img_next_"):
        # Navigate to next image
        # Format: img_next_{product_id}_{index}
        data = query.data.replace("img_next_", "")
        # Find last underscore (separates product_id from index)
        last_underscore = data.rfind("_")
        if last_underscore > 0:
            product_id = data[:last_underscore]
            current_index = int(data[last_underscore + 1:])
            
            product_info = context.user_data.get('current_product')
            if not product_info or str(product_info['product_id']) != str(product_id):
                await query.answer("❌ خطا در دریافت اطلاعات محصول", show_alert=True)
                return
            
            images = context.user_data.get('product_images', [])
            if not images or len(images) == 0:
                await query.answer("⚠️ تصویری موجود نیست", show_alert=True)
                return
            
            # Go to next image
            new_index = min(len(images) - 1, current_index + 1)
            context.user_data['current_image_index'] = new_index
            
            # Get current quantity and limits
            current_quantity = context.user_data.get('current_quantity', 1)
            effective_min = context.user_data.get('effective_min', 1)
            effective_max = context.user_data.get('effective_max', 999999)
            user_id = update.effective_user.id
            _, _, remaining_stock, _ = calculate_effective_quantity_limits(product_info, user_id)
            
            # Format message
            message = format_product_with_quantity(
                product_info, current_quantity, effective_min, effective_max, remaining_stock
            )
            
            # Create keyboard
            keyboard = create_quantity_keyboard(
                product_id, current_quantity, effective_min, effective_max,
                image_index=new_index,
                total_images=len(images)
            )
            
            # Update photo
            await query.edit_message_media(
                media=InputMediaPhoto(media=images[new_index], caption=message, parse_mode='Markdown'),
                reply_markup=keyboard
            )
            await query.answer()
    elif query.data == "img_info":
        # Just show image info (no action needed)
        await query.answer()
    elif query.data == "qty_display":
        # Just show current quantity (no action needed)
        await query.answer()
    elif query.data == "qty_min_reached":
        await query.answer("⚠️ به حداقل تعداد رسیده‌اید", show_alert=True)
    elif query.data == "qty_max_reached":
        await query.answer("⚠️ به حداکثر تعداد رسیده‌اید", show_alert=True)
    elif query.data.startswith("qty_add_cart_"):
        # Add to cart with current quantity
        product_id = query.data.replace("qty_add_cart_", "")
        product_info = context.user_data.get('current_product')
        if not product_info or str(product_info['product_id']) != str(product_id):
            await query.answer("❌ خطا در دریافت اطلاعات محصول", show_alert=True)
            return
        
        current_quantity = context.user_data.get('current_quantity', 1)
        user_id = update.effective_user.id
        
        # Validate quantity one more time before adding
        effective_min, effective_max, remaining_stock, current_cart_qty = calculate_effective_quantity_limits(
            product_info, user_id
        )
        
        # Check if quantity is valid
        if current_quantity < effective_min:
            await query.answer(f"❌ حداقل {effective_min} عدد باید انتخاب کنید", show_alert=True)
            return
        
        if current_quantity > effective_max:
            await query.answer(f"❌ حداکثر {effective_max} عدد می‌توانید انتخاب کنید", show_alert=True)
            return
        
        # Add to cart
        if add_to_cart(user_id, product_info['product_id'], current_quantity):
            context.user_data['awaiting_quantity'] = False
            cart_items = get_user_cart(user_id)
            cart_text = format_cart(cart_items)
            
            keyboard = create_cart_keyboard(context)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Cart should always be displayed as text message without product image
            # If it's a photo message, edit caption first, then try to convert to text
            # If it's a text message, just edit it
            try:
                if query.message.photo:
                    # It's a photo message - first update caption, then try to convert to text
                    # We'll use edit_message_media to convert photo to text
                    try:
                        # Try to convert photo message to text message using edit_message_media
                        # This doesn't work directly, so we'll just update caption and keep photo
                        # But user wants no image, so we'll delete and send new
                        await query.edit_message_caption(
                            caption=f"*✅ اضافه شد!*\n\n{cart_text}",
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                        # Now delete the photo message
                        await query.message.delete()
                        # Send new text message using context.bot.send_message (not reply_text to avoid triggering handlers)
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"*✅ اضافه شد!*\n\n{cart_text}",
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        # If editing caption fails, just delete and send new
                        await query.message.delete()
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"*✅ اضافه شد!*\n\n{cart_text}",
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                else:
                    # It's a text message - just edit it
                    await query.edit_message_text(
                        f"*✅ اضافه شد!*\n\n{cart_text}",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.error(f"Error updating cart message: {e}", exc_info=True)
                # If editing fails, try to delete and send new message
                try:
                    await query.message.delete()
                except:
                    pass
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"*✅ اضافه شد!*\n\n{cart_text}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            await query.answer("✅ به سبد خرید اضافه شد")
        else:
            await query.answer("❌ خطا در افزودن به سبد خرید", show_alert=True)
    elif query.data.startswith("qty_type_"):
        # Switch to typing mode
        product_id = query.data.replace("qty_type_", "")
        product_info = context.user_data.get('current_product')
        if not product_info or str(product_info['product_id']) != str(product_id):
            await query.answer("❌ خطا در دریافت اطلاعات محصول", show_alert=True)
            return
        
        context.user_data['awaiting_quantity'] = True
        context.user_data['awaiting_quantity_typing'] = True
        
        effective_min = context.user_data.get('effective_min', 1)
        
        message_text = (
            f"*⌨️ تعداد را تایپ کنید:*\n\n"
            f"*📊 حداقل:* {effective_min} عدد\n\n"
            f"تعداد مورد نظر خود را وارد کنید:"
        )
        
        # Check if message is a photo or text
        try:
            if query.message.photo:
                # It's a photo message - edit caption
                await query.edit_message_caption(
                    caption=message_text,
                    parse_mode='Markdown'
                )
            else:
                # It's a text message
                await query.edit_message_text(
                    message_text,
                    parse_mode='Markdown'
                )
        except Exception as e:
            # If editing fails, delete and send new message
            try:
                await query.message.delete()
            except:
                pass
            await query.message.reply_text(
                message_text,
                parse_mode='Markdown'
            )
        
        await query.answer()
    elif query.data == "cancel_order":
        clear_user_cart(user_id)
        context.user_data.clear()  # Clear any pending states
        # Clear any inline keyboard on the cart message
        try:
            await query.edit_message_text("*❌ سبد خرید لغو شد.*", reply_markup=None, parse_mode='Markdown')
        except Exception:
            pass
        await query.message.reply_text("*📱 بازگشت به کانال:*", reply_markup=create_channel_button(), parse_mode='Markdown')
        # Restore main menu
        reply_markup = create_main_menu_keyboard()
        await query.message.reply_text("*منوی اصلی:*", reply_markup=reply_markup, parse_mode='Markdown')
    elif query.data == "finish_order":
        logger.info(f"User {user_id} attempting to finish order")
        
        user_info = get_user_info(user_id)
        if user_info and user_info.get('phone_number') and user_info.get('first_name'):
            cart_items = get_user_cart(user_id)
            if not cart_items:
                await query.edit_message_text("**❌ سبد خالی!**", parse_mode='Markdown')
                return
            user_name = user_info.get('first_name', 'مشتری')
            phone = user_info.get('phone_number')
            order_id = create_order(user_id, cart_items, customer_name=user_name, customer_phone=phone)
            if order_id:
                clear_user_cart(user_id)
                cart_text = format_cart(cart_items)
                confirmation = (
                    f"**✅ سفارش ثبت شد!**\n\n"
                    f"**📋 شماره: {order_id:04d}**\n"
                    f"**👤 {user_name}**\n\n"
                    f"{cart_text}\n\n"
                    f"**✅ برای ادمین ارسال شد.**\n"
                    f"**⏰ به زودی تماس می‌گیریم.**\n\n"
                    f"**🙏 متشکریم!**"
                )
                await query.edit_message_text(confirmation, parse_mode='Markdown')
                
                # Calculate total amount and 2% discount
                total_amount = sum(item.get('price', 0) * item['quantity'] for item in cart_items)
                total_amount = float(total_amount)  # Convert Decimal to float
                discounted_amount = int(total_amount * 0.98)  # 2% off
                # Round down to nearest thousand
                discounted_amount = (discounted_amount // 1000) * 1000
                
                logger.info(f"Sending promo message. Total: {total_amount}, Discounted: {discounted_amount}")
                
                # Send promotional message with website link
                promo_keyboard = [[InlineKeyboardButton("🌐 homplast.com", url="https://homplast.com")]]
                promo_markup = InlineKeyboardMarkup(promo_keyboard)
                promo_message = (
                    f"😍 می‌دونستی اگه این سفارش رو از طریق وبسایت ما انجام می‌دادی، "
                    f"دو درصد تخفیف ویژه می‌گرفتی و بجای *{int(total_amount):,}* فقط "
                    f"*{discounted_amount:,}* تومان پرداخت می‌کردی!!!"
                )
                try:
                    await query.message.reply_text(
                        promo_message,
                        reply_markup=promo_markup,
                        parse_mode='Markdown'
                    )
                    logger.info("Promo message sent successfully")
                except Exception as e:
                    logger.error(f"Failed to send promo message: {e}")
                
                # Send channel button after promo
                await query.message.reply_text("**📱 بازگشت به کانال:**", reply_markup=create_channel_button(), parse_mode='Markdown')
                
                # Reset keyboard to main menu (removes any previous keyboards like "انصراف")
                main_menu = create_main_menu_keyboard()
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅  سفارش شما به شماره *{order_id:04d}* ثبت شد!\n\n"
                         f"📞 به زودی با شما تماس گرفته خواهد شد.\n\n"
                         f"برای سفارش جدید، به کانال مراجعه کنید",
                    reply_markup=main_menu,
                    parse_mode='Markdown'
                )
                
                admin_msg = (
                    f"**🔔 سفارش جدید!**\n\n"
                    f"**📋 #{order_id:04d}**\n"
                    f"**👤 {user_name}**\n"
                    f"**📱 {phone}**\n"
                    f"**🆔 {user_id}**\n\n"
                    f"{cart_text}"
                )
                try:
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Error: {e}")
        else:
            # Check if user has name but not phone, or missing both
            user_info = get_user_info(user_id)
            if user_info and user_info.get('first_name') and not user_info.get('phone_number'):
                await query.edit_message_text("**📱 لطفاً شماره تماس خود را وارد کنید:**", parse_mode='Markdown')
                context.user_data['awaiting_phone'] = True
            else:
                await query.edit_message_text("**✍️ لطفاً ابتدا ثبت نام کنید:**", parse_mode='Markdown')
                context.user_data['awaiting_name'] = True

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name input with validation"""
    if not context.user_data.get('awaiting_name'):
        return
    
    name = update.message.text.strip()
    
    # Validate name input
    is_valid, error_msg = InputValidator.validate_name(name)
    if not is_valid:
        await update.message.reply_text(f"**❌ {error_msg}**", parse_mode='Markdown')
        return
    
    # Sanitize name
    clean_name = InputValidator.sanitize_text(name)
    
    user_id = update.effective_user.id
    # Update user name in database using the proper function
    if not update_user_name(user_id, clean_name):
        await update.message.reply_text("**❌ خطا در ذخیره نام. لطفاً دوباره تلاش کنید.**", parse_mode='Markdown')
        return
    
    context.user_data['user_name'] = clean_name
    context.user_data['awaiting_name'] = False
    if context.user_data.get('editing_profile'):
        context.user_data.clear()
        reply_markup = create_main_menu_keyboard()
        await update.message.reply_text("**✅ نام شما بروز شد!**", reply_markup=reply_markup, parse_mode='Markdown')
        return
    context.user_data['awaiting_phone'] = True
    keyboard = [[KeyboardButton("📱 ارسال شماره", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        f"**✅ سلام {clean_name}!**\n\n"
        f"**شماره خود را ارسال کنید:**\n"
        f"(می‌توانید شماره را تایپ کنید یا از دکمه استفاده کنید)",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user orders"""
    user_id = update.effective_user.id
    orders = get_user_orders(user_id)
    if not orders:
        await update.message.reply_text("**📋 هنوز سفارشی ندارید.**", parse_mode='Markdown')
        await update.message.reply_text("**📱 بازگشت به کانال:**", reply_markup=create_channel_button(), parse_mode='Markdown')
        return
    text = "**🛒 سفارشات شما:**\n\n"
    for order in orders:
        emoji = {'pending': '⏳', 'confirmed': '✅', 'cancelled': '❌', 'completed': '✅'}.get(order['status'], '📦')
        # Convert date to Persian calendar
        persian_date = format_persian_date(order['created_at'])
        text += (
            f"{emoji} **#{order['order_id']:04d}**\n"
            f"{persian_date}\n"
            f"{order['total_amount']:,.0f} تومان - {order['item_count']} محصول\n"
            f"➖➖➖➖➖\n\n"
        )
    await update.message.reply_text(text, parse_mode='Markdown')
    await update.message.reply_text("**📱 بازگشت به کانال:**", reply_markup=create_channel_button(), parse_mode='Markdown')

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact input"""
    contact = update.message.contact
    user_id = update.effective_user.id
    if contact:
        phone = contact.phone_number
        update_user_phone(user_id, phone)
        if context.user_data.get('editing_phone'):
            context.user_data.clear()
            reply_markup = create_main_menu_keyboard()
            await update.message.reply_text("**✅ شماره شما بروز شد!**", reply_markup=reply_markup, parse_mode='Markdown')
            return
        if context.user_data.get('registering'):
            # Send admin notification for new user registration
            user_info = get_user_info(user_id)
            user_name = user_info.get('first_name', 'نامشخص') if user_info else 'نامشخص'
            username = update.effective_user.username or 'نامشخص'
            first_name_user = update.effective_user.first_name or 'نامشخص'
            last_name_user = update.effective_user.last_name or ''
            
            admin_registration_msg = (
                f"**👤 کاربر جدید ثبت نام کرد!**\n\n"
                f"**🆔 شناسه:** {user_id}\n"
                f"**👤 نام:** {user_name}\n"
                f"**📱 شماره:** {phone}\n"
                f"**@username:** @{username}\n"
                f"**نام تلگرام:** {first_name_user} {last_name_user}"
            )
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_registration_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error sending registration notification: {e}")
            
            context.user_data.clear()
            reply_markup = create_main_menu_keyboard()
            await update.message.reply_text(
                "**✅ ثبت نام با موفقیت انجام شد!**\n\nاطلاعات شما ذخیره شد.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        cart_items = get_user_cart(user_id)
        if not cart_items:
            reply_markup = create_main_menu_keyboard()
            await update.message.reply_text("**❌ سبد خالی!**", reply_markup=reply_markup, parse_mode='Markdown')
            return
        user_info = get_user_info(user_id)
        user_name = user_info.get('first_name', 'مشتری') if user_info else 'مشتری'
        phone = user_info.get('phone_number') if user_info else None
        order_id = create_order(user_id, cart_items, customer_name=user_name, customer_phone=phone)
        if order_id:
            clear_user_cart(user_id)
            cart_text = format_cart(cart_items)
            confirmation = (
                f"**✅ سفارش ثبت شد!**\n\n"
                f"**📋 شماره: {order_id:04d}**\n"
                f"**👤 {user_name}**\n\n"
                f"{cart_text}\n\n"
                f"**✅ برای ادمین ارسال شد.**\n"
                f"**⏰ به زودی تماس می‌گیریم.**\n\n"
                f"**🙏 متشکریم!**"
            )
            reply_markup = create_main_menu_keyboard()
            await update.message.reply_text(confirmation, reply_markup=reply_markup, parse_mode='Markdown')
            admin_msg = (
                f"**🔔 سفارش جدید!**\n\n"
                f"**📋 #{order_id:04d}**\n"
                f"**👤 {user_name}**\n"
                f"**📱 {phone}**\n"
                f"**🆔 {user_id}**\n\n"
                f"{cart_text}"
            )
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error: {e}")
            context.user_data.clear()

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user registration"""
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
            f"**✅ اطلاعات شما:**\n\n"
            f"**👤 نام:** {user_info.get('first_name', '')}\n"
            f"**📱 شماره:** {user_info.get('phone_number')}\n\n"
            f"برای ویرایش یکی از موارد را انتخاب کنید:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "**✍️ ثبت نام**\n\n**نام کامل خود را وارد کنید:**",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_name'] = True
        context.user_data['registering'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()

    # Handle cancel/return actions (useful for registration/other states, not product addition which uses inline buttons)
    if text == "🔙 بازگشت به منو" or text == "❌ انصراف" or "انصراف" in text or "بازگشت به منو" in text:
        context.user_data.clear()
        from telegram import ReplyKeyboardRemove
        remove_keyboard = ReplyKeyboardRemove(remove_keyboard=True)
        cancel_msg = "**✅ بازگشت به منوی اصلی**" if "بازگشت" in text else "**✅ عملیات لغو شد**"
        await update.message.reply_text(cancel_msg, reply_markup=remove_keyboard, parse_mode='Markdown')
        await update.message.reply_text("**📱 بازگشت به کانال:**", reply_markup=create_channel_button(), parse_mode='Markdown')
        reply_markup = create_main_menu_keyboard()
        await update.message.reply_text("**منوی اصلی:**", reply_markup=reply_markup, parse_mode='Markdown')
        return

    if text == "🔙 بازگشت به سبد":
        if context.user_data.get('awaiting_new_quantity'):
            context.user_data.clear()
            user_id = update.effective_user.id
            cart_items = get_user_cart(user_id)
            cart_text = format_cart(cart_items)
            keyboard = create_cart_keyboard(context)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"**✅ بازگشت به سبد خرید**\n\n{cart_text}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return

    if context.user_data.get('awaiting_quantity') and text in ["📦 سفارشات من", "✍️ ثبت نام", "☎️ پشتیبانی"]:
        context.user_data.clear()
        reply_markup = create_main_menu_keyboard()
        await update.message.reply_text("**✅ عملیات قبلی لغو شد.**", reply_markup=reply_markup, parse_mode='Markdown')
        if text == "📦 سفارشات من":
            await show_orders(update, context)
            return
        elif text == "✍️ ثبت نام":
            await register_user(update, context)
            return
        elif text == "☎️ پشتیبانی":
            admin_username = ADMIN_USERNAME if ADMIN_USERNAME.startswith('@') else f'@{ADMIN_USERNAME}'
            await update.message.reply_text(f"برای تماس با پشتیبانی، روی لینک زیر کلیک کنید:\n\n{admin_username}")
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
        
        # Sanitize phone input first
        phone = InputValidator.sanitize_text(phone)
        
        # Validate phone input
        is_valid, result = InputValidator.validate_phone(phone)
        if not is_valid:
            await update.message.reply_text(f"**❌ {result}**", parse_mode='Markdown')
            return
        
        # Get cleaned phone number from result
        clean_phone = result
        
        user_id = update.effective_user.id
        update_user_phone(user_id, clean_phone)
        if context.user_data.get('editing_phone'):
            context.user_data.clear()
            reply_markup = create_main_menu_keyboard()
            await update.message.reply_text("**✅ شماره شما بروز شد!**", reply_markup=reply_markup, parse_mode='Markdown')
            return
        if context.user_data.get('registering'):
            # Send admin notification for new user registration
            user_info = get_user_info(user_id)
            user_name = user_info.get('first_name', 'نامشخص') if user_info else 'نامشخص'
            username = update.effective_user.username or 'نامشخص'
            first_name_user = update.effective_user.first_name or 'نامشخص'
            last_name_user = update.effective_user.last_name or ''
            
            admin_registration_msg = (
                f"**👤 کاربر جدید ثبت نام کرد!**\n\n"
                f"**🆔 شناسه:** {user_id}\n"
                f"**👤 نام:** {user_name}\n"
                f"**📱 شماره:** {clean_phone}\n"
                f"**@username:** @{username}\n"
                f"**نام تلگرام:** {first_name_user} {last_name_user}"
            )
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_registration_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error sending registration notification: {e}")
            
            context.user_data.clear()
            reply_markup = create_main_menu_keyboard()
            await update.message.reply_text(
                "**✅ ثبت نام با موفقیت انجام شد!**\n\nاطلاعات شما ذخیره شد.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        cart_items = get_user_cart(user_id)
        if not cart_items:
            reply_markup = create_main_menu_keyboard()
            await update.message.reply_text("**❌ سبد خالی!**", reply_markup=reply_markup, parse_mode='Markdown')
            return
        user_info = get_user_info(user_id)
        user_name = user_info.get('first_name', 'مشتری') if user_info else 'مشتری'
        phone = user_info.get('phone_number') if user_info else None
        order_id = create_order(user_id, cart_items, customer_name=user_name, customer_phone=phone)
        if order_id:
            clear_user_cart(user_id)
            cart_text = format_cart(cart_items)
            confirmation = (
                f"**✅ سفارش ثبت شد!**\n\n"
                f"**📋 شماره: {order_id:04d}**\n"
                f"**👤 {user_name}**\n\n"
                f"{cart_text}\n\n"
                f"**✅ برای ادمین ارسال شد.**\n"
                f"**⏰ به زودی تماس می‌گیریم.**\n\n"
                f"**🙏 متشکریم!**"
            )
            reply_markup = create_main_menu_keyboard()
            await update.message.reply_text(confirmation, reply_markup=reply_markup, parse_mode='Markdown')
            admin_msg = (
                f"**🔔 سفارش جدید!**\n\n"
                f"**📋 #{order_id:04d}**\n"
                f"**👤 {user_name}**\n"
                f"**📱 {phone}**\n"
                f"**🆔 {user_id}**\n\n"
                f"{cart_text}"
            )
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error: {e}")
            context.user_data.clear()
        return
    if text == "📦 سفارشات من":
        await show_orders(update, context)
    elif text == "✍️ ثبت نام":
        await register_user(update, context)
    elif text == "🛒 مشاهده سبد خرید":
        user_id = update.effective_user.id
        cart_items = get_user_cart(user_id)
        if cart_items:
            cart_text = format_cart(cart_items)
            keyboard = create_cart_keyboard(context)
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"**🛒 سبد خرید شما:**\n\n{cart_text}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "**🛒 سبد خرید شما خالی است!**\n\n"
                "برای سفارش، از کانال دکمه «سفارش محصول» را بزنید.",
                parse_mode='Markdown'
            )
            await update.message.reply_text("**📱 بازگشت به کانال:**", reply_markup=create_channel_button(), parse_mode='Markdown')
    elif text == "☎️ پشتیبانی":
        admin_username = ADMIN_USERNAME if ADMIN_USERNAME.startswith('@') else f'@{ADMIN_USERNAME}'
        await update.message.reply_text(f"برای تماس با پشتیبانی، روی لینک زیر کلیک کنید:\n\n{admin_username}")
    else:
        await update.message.reply_text("**لطفاً از منو یا کانال انتخاب کنید.**", parse_mode='Markdown')

async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot version"""
    version_info = (
        f"**🤖 ربات فروش هوم پلاست**\n\n"
        f"**📌 نسخه:** {__version__}\n"
        f"**📅 آخرین بروزرسانی:** {__last_updated__}"
    )
    await update.message.reply_text(version_info, parse_mode='Markdown')

def main():
    """Main entry point - Supports both webhook and polling modes"""
    logger.info("Starting bot...")
    application = Application.builder().token(BOT_TOKEN).build()
    from telegram import BotCommand
    commands = [BotCommand("start", "شروع و منوی اصلی"), BotCommand("version", "نسخه ربات")]
    
    # Note: Bot works everywhere. Order notifications are sent via send_message to ADMIN_ID group.
    # If you want to restrict bot to private chats only, uncomment the filters below:
    # private_filter = filters.ChatType.PRIVATE
    # application.add_handler(CommandHandler("start", start, filters=private_filter))
    # ... (and add filter to other handlers)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("version", version_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.bot.set_my_commands(commands))
    logger.info("Bot started!")
    
    # Try to use webhook if configured, otherwise fallback to polling
    try:
        from config.settings import WEBHOOK_URL, WEBHOOK_PORT
        if WEBHOOK_URL and WEBHOOK_URL != '':
            logger.info(f"Configuring webhook to {WEBHOOK_URL}")
            webhook_path = f"/webhook/{BOT_TOKEN}"
            # For now, keep using polling as webhook requires additional setup
            # You can switch to webhook later when ready
            logger.info("Using polling mode (webhook setup requires additional configuration)")
            application.run_polling()
        else:
            application.run_polling()
    except Exception as e:
        logger.error(f"Error setting up webhook: {e}")
        logger.info("Falling back to polling mode")
        application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
