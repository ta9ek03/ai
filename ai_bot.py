import os
import io
import re
import time
import requests
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from deep_translator import GoogleTranslator
import google.generativeai as genai
from datetime import datetime

# ============================================================
#                     إعدادات البوت
# ============================================================
API_TOKEN = os.environ.get('API_TOKEN', '8761081408:AAHH6CoYLfzxGTTmPtrsHUHPxsfbTkJGDCc')
API_GEMINI = os.environ.get('API_GEMINI', 'AIzaSyA5pzOpKVcMGm6Aek82KoB3Pk94dYg3LX4')

bot = telebot.TeleBot(API_TOKEN, parse_mode=None)

# ============================================================
#                     بيانات المشرفين
# ============================================================
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8107616360'))
admins = set([ADMIN_ID])
banned_users = set()

# ============================================================
#                     ملفات البيانات
# ============================================================
USERS_FILE = 'users.txt'
IMAGE_FOLDER = 'images'

os.makedirs(IMAGE_FOLDER, exist_ok=True)

if not os.path.exists(USERS_FILE):
    open(USERS_FILE, 'w').close()

# ============================================================
#                     بيانات الجلسات
# ============================================================
users = {}
broadcast_list = []
user_sessions = {}
user_states = {}


# ============================================================
#                     دوال مساعدة
# ============================================================

def is_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)

def translate(text, source='auto', target='ar'):
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception:
        return text

def load_users_list():
    with open(USERS_FILE, 'r') as f:
        return [u.strip() for u in f.read().splitlines() if u.strip()]

def save_user(user_id, username, full_name):
    user_id_str = str(user_id)
    users_list = load_users_list()
    new_user = user_id_str not in users_list

    if new_user:
        with open(USERS_FILE, 'a') as f:
            f.write(user_id_str + '\n')
        total_users = len(users_list) + 1
        try:
            bot.send_message(
                ADMIN_ID,
                f"👾 <b>مستخدم جديد دخل البوت</b>\n\n"
                f"👤 الاسم: <b>{full_name or 'غير متوفر'}</b>\n"
                f"🔖 المعرف: @{username if username else 'غير متوفر'}\n"
                f"🆔 الآيدي: <code>{user_id}</code>\n\n"
                f"📊 إجمالي الأعضاء: <b>{total_users}</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

def get_statistics():
    users_list = load_users_list()
    total = len(users_list)
    last_ten = users_list[-10:]
    last_str = "\n".join([f"🆔 <code>{uid}</code>" for uid in last_ten])
    return (
        f"📊 <b>إحصائيات البوت</b>\n\n"
        f"👥 إجمالي المستخدمين: <b>{total}</b>\n\n"
        f"🕐 آخر 10 مستخدمين:\n{last_str}"
    )

def check_banned(user_id, chat_id):
    if user_id in banned_users:
        bot.send_message(chat_id, "🚫 أنت محظور من استخدام هذا البوت.")
        return True
    return False


# ============================================================
#               ريلي كل الرسائل للمشرف
# ============================================================

@bot.message_handler(func=lambda m: True, content_types=[
    'text', 'photo', 'video', 'audio', 'voice', 'document',
    'sticker', 'animation', 'location', 'contact', 'video_note'
])
def forward_to_admin(message):
    uid = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.first_name or ''

    save_user(uid, username, full_name)
    if uid not in users:
        users[uid] = {"username": username, "joined": datetime.now()}
        if uid not in broadcast_list:
            broadcast_list.append(uid)

    if uid == ADMIN_ID:
        handle_admin_text(message)
        return

    if check_banned(uid, message.chat.id):
        return

    if message.content_type == 'text' and message.text and message.text.startswith('/'):
        handle_commands(message)
        return

    # توجيه للمشرف
    try:
        header = (
            f"📨 <b>رسالة من مستخدم</b>\n"
            f"👤 {full_name}\n"
            f"🔖 @{username if username else 'بدون معرف'}\n"
            f"🆔 <code>{uid}</code>\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"{'─'*28}"
        )
        bot.send_message(ADMIN_ID, header, parse_mode="HTML")
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    except Exception as e:
        print(f"خطأ في التوجيه: {e}")

    if message.content_type == 'text':
        text = message.text.strip()
        if text.lower().startswith('بوتي'):
            ai_chat(message)
        else:
            bot.send_message(
                message.chat.id,
                "💬 لاستخدام الذكاء الاصطناعي اكتب: <b>بوتي</b> + سؤالك\n"
                "🖼 لإنشاء صورة: /image + الوصف\n"
                "🖼 نموذج آخر: /image2 + الوصف\n"
                "🔬 نانو: /nano + الوصف\n"
                "📝 كتابة نص: /Write + النص",
                parse_mode="HTML"
            )


def handle_admin_text(message):
    if message.reply_to_message:
        try:
            text = message.reply_to_message.text or ''
            match = re.search(r'🆔 (\d+)', text)
            if match:
                target_uid = int(match.group(1))
                bot.copy_message(target_uid, message.chat.id, message.message_id)
                bot.send_message(ADMIN_ID, "✅ تم إرسال الرد للمستخدم.", parse_mode="HTML")
                return
        except Exception as e:
            print(f"خطأ في الرد: {e}")

    if message.content_type == 'text' and message.text and message.text.startswith('/'):
        handle_commands(message)


# ============================================================
#                     أوامر البوت
# ============================================================

def handle_commands(message):
    cmd = message.text.split()[0].lower() if message.text else ''
    if cmd == '/start':
        send_welcome(message)
    elif cmd == '/clear':
        close_chat(message)
    elif cmd == '/image':
        create_image(message)
    elif cmd == '/image2':
        create_image2(message)
    elif cmd == '/nano':
        create_nano_image(message)
    elif cmd in ['/write', '/Write']:
        create_text_image(message)
    elif cmd == '/admin':
        admin_panel(message)
    elif cmd == '/stats':
        if message.from_user.id in admins:
            bot.send_message(message.chat.id, get_statistics(), parse_mode="HTML")
    elif cmd == '/help':
        send_help(message)
    elif cmd == '/broadcast':
        if message.from_user.id in admins:
            msg = bot.send_message(message.chat.id, "✉️ أرسل الرسالة التي تريد بثها:")
            bot.register_next_step_handler(msg, do_broadcast)


# ============================================================
#                     /start
# ============================================================

def send_welcome(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/ta9ek"),
        InlineKeyboardButton("🖼 إنشاء صورة", switch_inline_query_current_chat="/image "),
        InlineKeyboardButton("❓ مساعدة", callback_data="help"),
    )
    bot.send_message(
        message.chat.id,
        "✨ <b>أهلاً بك في بوت الذكاء الاصطناعي!</b> 🤖\n\n"
        "أنا قادر على مساعدتك في:\n"
        "🧠 الإجابة على أسئلتك — اكتب: <b>بوتي</b> + سؤالك\n"
        "🖼 إنشاء صور (Banana Pro) — <code>/image وصف الصورة</code>\n"
        "🖼 إنشاء صور (Banana Nano 2) — <code>/image2 وصف الصورة</code>\n"
        "🔬 إنشاء صور (Nano Banana) — <code>/nano وصف الصورة</code>\n"
        "📝 كتابة نص على ورقة — <code>/Write النص</code>\n"
        "🗑 مسح سياق المحادثة — <code>/clear</code>\n\n"
        "<i>صلي على النبي 🔒</i>",
        reply_markup=markup,
        parse_mode="HTML"
    )


# ============================================================
#                     /help
# ============================================================

def send_help(message):
    bot.send_message(
        message.chat.id,
        "📚 <b>دليل استخدام البوت</b>\n\n"
        "🔹 <b>بوتي [سؤالك]</b> — محادثة مع الذكاء الاصطناعي\n"
        "🔹 <b>/image [وصف]</b> — إنشاء صورة (Banana Pro)\n"
        "🔹 <b>/image2 [وصف]</b> — إنشاء صورة (Banana Nano 2)\n"
        "🔹 <b>/nano [وصف]</b> — إنشاء صورة (Nano Banana)\n"
        "🔹 <b>/Write [نص]</b> — كتابة نص على ورقة\n"
        "🔹 <b>/clear</b> — مسح جلسة المحادثة\n"
        "🔹 <b>/start</b> — القائمة الرئيسية\n\n"
        "📌 يمكنك إرسال أي رسالة أو صورة أو ملف وسيصل للمشرف.",
        parse_mode="HTML"
    )


# ============================================================
#                     /clear
# ============================================================

def close_chat(message):
    uid = message.chat.id
    if uid in user_sessions:
        del user_sessions[uid]
    bot.send_message(
        message.chat.id,
        "🗑 <b>تم مسح سياق المحادثة.</b>\n"
        "يمكنك البدء من جديد بكتابة: <b>بوتي</b> + سؤالك",
        parse_mode="HTML"
    )


# ============================================================
#               الذكاء الاصطناعي - بوتي
# ============================================================

def ai_chat(message):
    uid = message.chat.id
    if check_banned(uid, uid):
        return

    user_content = re.sub(r'^بوتي\s*', '', message.text, flags=re.IGNORECASE).strip()
    if not user_content:
        bot.send_message(uid, "✏️ أرسل سؤالك بعد كلمة <b>بوتي</b>", parse_mode="HTML")
        return

    if uid not in user_sessions:
        genai.configure(api_key=API_GEMINI)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            },
            system_instruction=(
                "You are a helpful, friendly AI assistant. "
                "Answer in the same language the user writes in. "
                "If the user writes Arabic, reply in Arabic. "
                "Be concise, accurate, and helpful."
            ),
        )
        user_sessions[uid] = model.start_chat(history=[])

    chat_session = user_sessions[uid]
    typing_msg = bot.send_message(uid, "⏳ جارٍ التفكير...")
    bot.send_chat_action(uid, 'typing')

    try:
        response = chat_session.send_message(user_content)
        reply_text = response.text.strip()

        try:
            bot.delete_message(uid, typing_msg.message_id)
        except Exception:
            pass

        max_len = 4000
        for i in range(0, len(reply_text), max_len):
            chunk = reply_text[i:i+max_len]
            bot.send_message(uid, f"🤖 <b>الذكاء الاصطناعي:</b>\n\n{chunk}", parse_mode="HTML")

    except Exception as e:
        try:
            bot.delete_message(uid, typing_msg.message_id)
        except Exception:
            pass
        bot.send_message(uid, f"⚠️ حدث خطأ: <code>{e}</code>", parse_mode="HTML")


# ============================================================
#           إنشاء الصور — ثلاثة نماذج
# ============================================================

IMAGE_APIS = {
    "banana_pro":   "http://art.nowtechai.com/art?name={prompt}",
    "banana_nano2": "https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true",
    "nano_banana":  "https://image.pollinations.ai/prompt/{prompt}?width=512&height=512&model=flux&nologo=true",
}

def fetch_and_send_image(chat_id, prompt_ar, api_key, caption_extra=""):
    prompt_en = translate(prompt_ar, source='auto', target='en')
    api_url = IMAGE_APIS[api_key].format(prompt=requests.utils.quote(prompt_en))

    processing_msg = bot.send_message(
        chat_id,
        f"🎨 <b>جارٍ إنشاء الصورة...</b>\n📝 الوصف: {prompt_ar}",
        parse_mode="HTML"
    )

    try:
        if api_key == "banana_pro":
            resp = requests.get(api_url, timeout=30)
            data = resp.json()
            if data.get("code") == 200 and data.get("data"):
                img_url = data["data"][0]["img_url"]
                img_data = requests.get(img_url, timeout=30).content
            else:
                bot.edit_message_text("❌ لم أتمكن من إنشاء الصورة. حاول وصفاً مختلفاً.", chat_id, processing_msg.message_id)
                return
        else:
            img_data = requests.get(api_url, timeout=60).content
            if len(img_data) < 1000:
                bot.edit_message_text("❌ لم يتم الحصول على صورة صالحة. جرب مرة أخرى.", chat_id, processing_msg.message_id)
                return

        try:
            bot.delete_message(chat_id, processing_msg.message_id)
        except Exception:
            pass

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/ta9ek"),
        )

        caption = (
            f"✅ <b>تم إنشاء الصورة بنجاح!</b>\n"
            f"📝 الوصف: {prompt_ar}\n"
            f"🤖 النموذج: {caption_extra}"
        )

        bot.send_photo(
            chat_id,
            photo=io.BytesIO(img_data),
            caption=caption,
            parse_mode="HTML",
            reply_markup=markup
        )

        try:
            bot.send_photo(
                ADMIN_ID,
                photo=io.BytesIO(img_data),
                caption=f"🖼 صورة أُنشئت من المستخدم {chat_id}\n📝 {prompt_ar}\n🤖 {caption_extra}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    except Exception as e:
        try:
            bot.delete_message(chat_id, processing_msg.message_id)
        except Exception:
            pass
        bot.send_message(chat_id, f"⚠️ حدث خطأ: <code>{e}</code>", parse_mode="HTML")


@bot.message_handler(commands=['image'])
def create_image(message):
    uid = message.chat.id
    if check_banned(uid, uid):
        return
    prompt = message.text.replace('/image', '').strip()
    if not prompt:
        bot.send_message(uid, "✏️ أرسل وصف الصورة بعد الأمر:\n<code>/image قطة تجلس في الفضاء</code>", parse_mode="HTML")
        return
    fetch_and_send_image(uid, prompt, "banana_pro", "🍌 Banana Pro")


@bot.message_handler(commands=['image2'])
def create_image2(message):
    uid = message.chat.id
    if check_banned(uid, uid):
        return
    prompt = message.text.replace('/image2', '').strip()
    if not prompt:
        bot.send_message(uid, "✏️ أرسل وصف الصورة بعد الأمر:\n<code>/image2 منظر طبيعي</code>", parse_mode="HTML")
        return
    fetch_and_send_image(uid, prompt, "banana_nano2", "🍌 Banana Nano 2")


@bot.message_handler(commands=['nano'])
def create_nano_image(message):
    uid = message.chat.id
    if check_banned(uid, uid):
        return
    prompt = message.text.replace('/nano', '').strip()
    if not prompt:
        bot.send_message(uid, "✏️ أرسل وصف الصورة بعد الأمر:\n<code>/nano رجل يمشي في الغابة</code>", parse_mode="HTML")
        return
    fetch_and_send_image(uid, prompt, "nano_banana", "🔬 Nano Banana")


# ============================================================
#                     /Write
# ============================================================

@bot.message_handler(commands=['Write', 'write'])
def create_text_image(message):
    uid = message.chat.id
    if check_banned(uid, uid):
        return
    text = re.sub(r'^/[Ww]rite\s*', '', message.text).strip()
    if not text:
        bot.send_message(uid, "✏️ أرسل النص بعد الأمر:\n<code>/Write مرحباً بالعالم</code>", parse_mode="HTML")
        return

    text_en = translate(text, source='auto', target='en') if is_arabic(text) else text
    bot.send_message(uid, "⏳ جارٍ إنشاء الصورة...", parse_mode="HTML")

    try:
        img_url = f"https://apis.xditya.me/write?text={requests.utils.quote(text_en)}"
        img_data = requests.get(img_url, timeout=30).content

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/ta9ek"),
        )

        bot.send_photo(
            uid,
            photo=io.BytesIO(img_data),
            caption="✅ <b>تم إنشاء صورة النص بنجاح!</b>",
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception as e:
        bot.send_message(uid, f"⚠️ حدث خطأ: <code>{e}</code>", parse_mode="HTML")


# ============================================================
#                     لوحة الإدارة
# ============================================================

def admin_panel(message):
    uid = message.from_user.id
    if uid not in admins:
        bot.send_message(message.chat.id, "🚫 ليس لديك صلاحية الوصول.")
        return
    bot.send_message(message.chat.id, "🛠 <b>لوحة التحكم</b>", reply_markup=get_admin_menu(), parse_mode="HTML")


def get_admin_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="manage_users"),
        InlineKeyboardButton("📊 الإحصائيات", callback_data="statistics"),
        InlineKeyboardButton("📢 بث رسالة", callback_data="broadcast"),
        InlineKeyboardButton("📌 بث مع تثبيت", callback_data="broadcast_pin"),
        InlineKeyboardButton("📋 قائمة المحظورين", callback_data="list_banned"),
    )
    return markup


def get_manage_users_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🚫 حظر", callback_data="ban_user"),
        InlineKeyboardButton("🔓 فك حظر", callback_data="unban_user"),
        InlineKeyboardButton("➕ إضافة أدمن", callback_data="add_admin"),
        InlineKeyboardButton("➖ حذف أدمن", callback_data="remove_admin"),
        InlineKeyboardButton("🔙 رجوع", callback_data="back_admin"),
    )
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id

    if call.data == "help":
        send_help(call.message)
        bot.answer_callback_query(call.id)
        return

    if uid not in admins:
        bot.answer_callback_query(call.id, "🚫 ليس لديك صلاحية.", show_alert=True)
        return

    bot.answer_callback_query(call.id)

    if call.data == "manage_users":
        bot.send_message(uid, "👥 <b>إدارة المستخدمين</b>", reply_markup=get_manage_users_menu(), parse_mode="HTML")

    elif call.data == "statistics":
        bot.send_message(uid, get_statistics(), parse_mode="HTML")

    elif call.data == "broadcast":
        msg = bot.send_message(uid, "✉️ أرسل الرسالة التي تريد بثها لجميع المستخدمين:")
        bot.register_next_step_handler(msg, do_broadcast, pin=False)

    elif call.data == "broadcast_pin":
        msg = bot.send_message(uid, "📌 أرسل الرسالة التي تريد بثها مع تثبيت:")
        bot.register_next_step_handler(msg, do_broadcast, pin=True)

    elif call.data == "list_banned":
        if banned_users:
            ids_str = "\n".join([f"<code>{i}</code>" for i in banned_users])
            bot.send_message(uid, f"🚫 <b>المحظورون:</b>\n{ids_str}", parse_mode="HTML")
        else:
            bot.send_message(uid, "✅ لا يوجد أي مستخدم محظور.")

    elif call.data == "ban_user":
        msg = bot.send_message(uid, "🆔 أرسل آيدي المستخدم لحظره:")
        bot.register_next_step_handler(msg, ban_user_step)

    elif call.data == "unban_user":
        msg = bot.send_message(uid, "🆔 أرسل آيدي المستخدم لفك الحظر عنه:")
        bot.register_next_step_handler(msg, unban_user_step)

    elif call.data == "add_admin":
        msg = bot.send_message(uid, "🆔 أرسل آيدي المستخدم لتعيينه أدمن:")
        bot.register_next_step_handler(msg, add_admin_step)

    elif call.data == "remove_admin":
        msg = bot.send_message(uid, "🆔 أرسل آيدي الأدمن لإزالته:")
        bot.register_next_step_handler(msg, remove_admin_step)

    elif call.data == "back_admin":
        bot.send_message(uid, "🛠 <b>لوحة التحكم</b>", reply_markup=get_admin_menu(), parse_mode="HTML")


# ============================================================
#               خطوات الإدارة
# ============================================================

def ban_user_step(message):
    try:
        target = int(message.text.strip())
        banned_users.add(target)
        bot.send_message(message.chat.id, f"✅ تم حظر المستخدم <code>{target}</code>", parse_mode="HTML")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ آيدي غير صحيح.")

def unban_user_step(message):
    try:
        target = int(message.text.strip())
        banned_users.discard(target)
        bot.send_message(message.chat.id, f"✅ تم فك الحظر عن <code>{target}</code>", parse_mode="HTML")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ آيدي غير صحيح.")

def add_admin_step(message):
    try:
        target = int(message.text.strip())
        admins.add(target)
        bot.send_message(message.chat.id, f"✅ تمت إضافة <code>{target}</code> كأدمن.", parse_mode="HTML")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ آيدي غير صحيح.")

def remove_admin_step(message):
    try:
        target = int(message.text.strip())
        if target == ADMIN_ID:
            bot.send_message(message.chat.id, "⚠️ لا يمكن إزالة المالك الرئيسي.")
            return
        admins.discard(target)
        bot.send_message(message.chat.id, f"✅ تمت إزالة <code>{target}</code> من الأدمن.", parse_mode="HTML")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ آيدي غير صحيح.")


# ============================================================
#               البث للجميع
# ============================================================

def do_broadcast(message, pin=False):
    users_list = load_users_list()
    success = 0
    fail = 0
    bot.send_message(message.chat.id, f"📤 جارٍ الإرسال لـ {len(users_list)} مستخدم...")
    for uid_str in users_list:
        try:
            sent = bot.copy_message(int(uid_str), message.chat.id, message.message_id)
            if pin:
                try:
                    bot.pin_chat_message(int(uid_str), sent.message_id)
                except Exception:
                    pass
            success += 1
            time.sleep(0.05)
        except Exception:
            fail += 1
    bot.send_message(
        message.chat.id,
        f"✅ <b>اكتمل البث!</b>\n✔️ نجح: {success}\n❌ فشل: {fail}",
        parse_mode="HTML"
    )


# ============================================================
#                     تشغيل البوت
# ============================================================

if __name__ == "__main__":
    print("🤖 البوت يعمل...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
