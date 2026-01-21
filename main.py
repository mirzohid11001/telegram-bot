import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ChatType, ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN

# ================= GLOBAL SAQLASH =================
groups = {}          # group_id -> data
admin_state = {}     # admin_id -> group_id
subscribers = set()  # botga yozganlar


def ensure_group(gid: int):
    if gid not in groups:
        groups[gid] = {
            "required": 1,
            "invites": {},     # user_id -> count
            "bad_words": set()
        }


# ================= BOT =================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# ================= PRIVATE START =================
@dp.message(Command("start"), F.chat.type == ChatType.PRIVATE)
async def start_private(message: Message):
    subscribers.add(message.from_user.id)
    await message.answer(
        """
🤖 <b>Bot boshqaruv paneli</b>

1️⃣ Botni guruhga <b>ADMIN</b> qiling
2️⃣ Guruhda yozing:
<code>/setgroup</code>

3️⃣ Keyin botga PRIVATE yozing:

<code>/setinvites 2</code> — nechta odam qo‘shish
<code>/addbad so‘z</code> — 18+ so‘z qo‘shish
<code>/delbad so‘z</code> — 18+ so‘zni o‘chirish
<code>/badlist</code> — 18+ ro‘yxat
<code>/stats</code> — statistika
        """
    )


# ================= GROUP: SET GROUP =================
@dp.message(Command("setgroup"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def set_group(message: Message):
    admins = await bot.get_chat_administrators(message.chat.id)
    if message.from_user.id not in [a.user.id for a in admins]:
        return

    admin_state[message.from_user.id] = message.chat.id
    ensure_group(message.chat.id)

    await message.answer("✅ Guruh tanlandi. Endi botga PRIVATE yozing.")


# ================= PRIVATE: SET INVITES =================
@dp.message(Command("setinvites"), F.chat.type == ChatType.PRIVATE)
async def set_invites(message: Message):
    admin_id = message.from_user.id
    if admin_id not in admin_state:
        await message.answer("Avval guruhda /setgroup yozing")
        return

    try:
        n = int(message.text.split()[1])
        if n < 1:
            raise ValueError
    except:
        await message.answer("Foydalanish: /setinvites 2")
        return

    gid = admin_state[admin_id]
    ensure_group(gid)
    groups[gid]["required"] = n

    await message.answer(f"✅ Invite soni <b>{n}</b> qilib belgilandi")


# ================= PRIVATE: ADD BAD WORD =================
@dp.message(Command("addbad"), F.chat.type == ChatType.PRIVATE)
async def add_bad(message: Message):
    admin_id = message.from_user.id
    if admin_id not in admin_state:
        return

    try:
        word = message.text.split(maxsplit=1)[1].lower()
    except:
        await message.answer("Foydalanish: /addbad so‘z")
        return

    gid = admin_state[admin_id]
    ensure_group(gid)
    groups[gid]["bad_words"].add(word)

    await message.answer(f"🚫 Qo‘shildi: <b>{word}</b>")


# ================= PRIVATE: DEL BAD WORD =================
@dp.message(Command("delbad"), F.chat.type == ChatType.PRIVATE)
async def del_bad(message: Message):
    admin_id = message.from_user.id
    if admin_id not in admin_state:
        return

    try:
        word = message.text.split(maxsplit=1)[1].lower()
    except:
        await message.answer("Foydalanish: /delbad so‘z")
        return

    gid = admin_state[admin_id]
    ensure_group(gid)
    groups[gid]["bad_words"].discard(word)

    await message.answer(f"🗑️ O‘chirildi: <b>{word}</b>")


# ================= PRIVATE: BAD LIST =================
@dp.message(Command("badlist"), F.chat.type == ChatType.PRIVATE)
async def bad_list(message: Message):
    admin_id = message.from_user.id
    if admin_id not in admin_state:
        return

    gid = admin_state[admin_id]
    ensure_group(gid)
    words = groups[gid]["bad_words"]

    if not words:
        await message.answer("🚫 18+ so‘zlar yo‘q")
    else:
        await message.answer("🚫 18+ so‘zlar:\n" + "\n".join(words))


# ================= PRIVATE: STATISTIKA =================
@dp.message(Command("stats"), F.chat.type == ChatType.PRIVATE)
async def stats_private(message: Message):
    admin_id = message.from_user.id
    if admin_id not in admin_state:
        await message.answer("Avval guruhda /setgroup yozing")
        return

    gid = admin_state[admin_id]
    ensure_group(gid)
    data = groups[gid]

    required = data["required"]
    bad_count = len(data["bad_words"])
    invite_map = data["invites"]

    total_invites = sum(invite_map.values())
    total_users = len(invite_map)

    top = sorted(invite_map.items(), key=lambda x: x[1], reverse=True)[:5]
    if top:
        top_text = "\n".join(
            [
                f"{i+1}. <a href='tg://user?id={user_id}'>{user_id}</a> — {cnt}"
                for i, (user_id, cnt) in enumerate(top)
            ]
        )
    else:
        top_text = "Hali yo‘q"

    await message.answer(
        "📊 <b>GURUH STATISTIKASI</b>\n\n"
        f"👥 Talab qilingan invite: <b>{required}</b>\n"
        f"🧮 Jami invite qilingan: <b>{total_invites}</b>\n"
        f"👤 Invite qilganlar: <b>{total_users}</b>\n"
        f"🚫 18+ so‘zlar soni: <b>{bad_count}</b>\n\n"
        f"🏆 <b>TOP 5:</b>\n{top_text}\n\n"
        f"🤖 Bot obunachilari: <b>{len(subscribers)}</b>"
    )


# ================= GROUP: JOIN / LEAVE DELETE =================
@dp.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.new_chat_members
)
@dp.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.left_chat_member
)
async def delete_join_leave(message: Message):
    try:
        await message.delete()
    except:
        pass


# ================= GROUP FILTER =================
@dp.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def group_filter(message: Message):
    gid = message.chat.id
    ensure_group(gid)

    # adminlarni tekshirmaymiz
    admins = await bot.get_chat_administrators(gid)
    if message.from_user.id in [a.user.id for a in admins]:
        return

    text = (message.text or "").lower()

    # 18+ tekshiruv
    for w in groups[gid]["bad_words"]:
        if w in text:
            await message.delete()
            warn = await message.answer(
                f"⚠️ <a href='tg://user?id={message.from_user.id}'>Foydalanuvchi</a>, "
                "18+ so‘z taqiqlangan!"
            )
            await asyncio.sleep(5)
            await warn.delete()
            return

    # invite tekshiruv
    user_id = message.from_user.id
    if groups[gid]["invites"].get(user_id, 0) < groups[gid]["required"]:
        await message.delete()
        warn = await message.answer(
            f"⚠️ <a href='tg://user?id={user_id}'>Foydalanuvchi</a>, "
            f"{groups[gid]['required']} ta odam qo‘shing"
        )
        await asyncio.sleep(5)
        await warn.delete()


# ================= RUN =================
async def main():
    print("🤖 Bot ishga tushdi (FINAL)")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
