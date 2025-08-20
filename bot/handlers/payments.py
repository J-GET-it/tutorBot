from decimal import Decimal
from django.conf import settings
from telebot.types import CallbackQuery, Message
from bot import bot
from bot.models import User, Payment, PaymentHistory
from bot.keyboards import (
    generate_payment_menu_keyboard,
    generate_payment_months_keyboard,
    generate_payment_confirmation_keyboard,
    generate_check_payment_keyboard,
    UNIVERSAL_BUTTONS,
    MONTH_NAMES
)
from bot.pricing import get_price_by_class, TEST_PRICE
from bot.yookassa_client import YooKassaClient
from django.utils import timezone


def payment_menu(call: CallbackQuery) -> None:
    """Обработчик меню оплаты"""
    markup = generate_payment_menu_keyboard()
    text = "💰 Оплата занятий\n\n"
    text += "Выберите действие:"
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        text=text,
        reply_markup=markup,
        message_id=call.message.message_id
    )


def start_payment(call: CallbackQuery) -> None:
    """Начинает процесс оплаты - показывает выбор месяца"""
    try:
        user = User.objects.get(telegram_id=str(call.from_user.id))
        
        if not user.is_registered:
            bot.answer_callback_query(call.id, "Сначала завершите регистрацию!")
            return
        
        # Получаем цену для класса пользователя
        price_info = get_price_by_class(user.course_or_class)
        
        if not price_info:
            text = "❌ Не удалось определить стоимость для вашего класса.\n"
            text += "Обратитесь к администратору."
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                text=text,
                reply_markup=UNIVERSAL_BUTTONS,
                message_id=call.message.message_id
            )
            return
        
        markup = generate_payment_months_keyboard()
        text = f"💳 Оплата занятий\n\n"
        text += f"📚 Ваш класс: {user.course_or_class}\n"
        text += f"💯 Тариф: {price_info['name']}\n"
        text += f"💰 Стоимость: {TEST_PRICE} руб. (тестовый режим)\n"
        text += f"📝 {price_info['description']}\n\n"
        text += "Выберите месяц для оплаты:"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    
    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "Пользователь не найден")


def select_payment_month(call: CallbackQuery) -> None:
    """Обработчик выбора месяца для оплаты"""
    try:
        # Парсим callback_data: pay_month_{month}_{year}
        parts = call.data.split('_')
        if len(parts) != 4:
            bot.answer_callback_query(call.id, "Ошибка в данных")
            return
        
        month = int(parts[2])
        year = int(parts[3])
        
        user = User.objects.get(telegram_id=str(call.from_user.id))
        
        # Проверяем, не оплачен ли уже этот месяц
        if PaymentHistory.is_month_paid(user, month, year):
            bot.answer_callback_query(call.id, f"Месяц {MONTH_NAMES[month]} {year} уже оплачен!")
            return
        
        # Получаем информацию о цене
        price_info = get_price_by_class(user.course_or_class)
        
        if not price_info:
            bot.answer_callback_query(call.id, "Ошибка определения цены")
            return
        
        markup = generate_payment_confirmation_keyboard(month, year)
        text = f"💳 Подтверждение оплаты\n\n"
        text += f"👤 Ученик: {user.full_name}\n"
        text += f"📚 Класс: {user.course_or_class}\n"
        text += f"💯 Тариф: {price_info['name']}\n"
        text += f"📅 Месяц: {MONTH_NAMES[month]} {year}\n"
        text += f"💰 К оплате: {TEST_PRICE} руб. (тестовый режим)\n\n"
        text += "Подтвердите оплату:"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    
    except (ValueError, User.DoesNotExist) as e:
        bot.answer_callback_query(call.id, "Ошибка обработки")


def confirm_payment(call: CallbackQuery) -> None:
    """Подтверждение и создание платежа"""
    try:
        # Парсим callback_data: confirm_payment_{month}_{year}
        parts = call.data.split('_')
        if len(parts) != 4:
            bot.answer_callback_query(call.id, "Ошибка в данных")
            return
        
        month = int(parts[2])
        year = int(parts[3])
        
        user = User.objects.get(telegram_id=str(call.from_user.id))
        
        # Проверяем повторно, не оплачен ли месяц
        if PaymentHistory.is_month_paid(user, month, year):
            bot.answer_callback_query(call.id, "Этот месяц уже оплачен!")
            return
        
        # Получаем информацию о цене
        price_info = get_price_by_class(user.course_or_class)
        
        if not price_info:
            bot.answer_callback_query(call.id, "Ошибка определения цены")
            return
        
        # Создаем платеж через ЮKassa
        yookassa_client = YooKassaClient()
        
        amount = Decimal(str(TEST_PRICE))  # Используем тестовую цену
        description = f"Оплата занятий за {MONTH_NAMES[month]} {year} - {price_info['name']}"
        
        metadata = {
            "user_id": user.telegram_id,
            "month": month,
            "year": year,
            "pricing_plan": price_info['key']
        }
        
        print(f"Создаем платеж для пользователя {user.telegram_id}")
        print(f"Сумма: {amount}, Описание: {description}")
        print(f"Метаданные: {metadata}")
        
        yookassa_response = yookassa_client.create_payment(
            amount=amount,
            description=description,
            metadata=metadata
        )
        
        print(f"Ответ от ЮKassa: {yookassa_response}")
        
        if not yookassa_response:
            text = "❌ Ошибка при создании платежа.\n\n"
            text += "Возможные причины:\n"
            text += "• Неправильные настройки ЮKassa\n"
            text += "• Проблемы с интернет-соединением\n"
            text += "• Ошибка на стороне ЮKassa\n\n"
            text += "Попробуйте позже или обратитесь к администратору."
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                text=text,
                reply_markup=UNIVERSAL_BUTTONS,
                message_id=call.message.message_id
            )
            return
        
        # Сохраняем платеж в базу данных
        payment = Payment.objects.create(
            user=user,
            yookassa_payment_id=yookassa_response['id'],
            amount=amount,
            status=yookassa_response['status'],
            description=description,
            payment_month=month,
            payment_year=year,
            pricing_plan=price_info['key']
        )
        
        # Получаем ссылку для оплаты
        payment_url = yookassa_response['confirmation']['confirmation_url']
        
        # Создаем клавиатуру с ссылкой на оплату и кнопкой проверки
        markup = generate_check_payment_keyboard(payment.yookassa_payment_id, month, year)
        
        text = f"✅ Платеж создан!\n\n"
        text += f"💰 Сумма: {amount} руб.\n"
        text += f"📅 За месяц: {MONTH_NAMES[month]} {year}\n"
        text += f"💯 Тариф: {price_info['name']}\n\n"
        text += "1️⃣ Перейдите по ссылке и оплатите\n"
        text += "2️⃣ После оплаты нажмите 'Проверить оплату'\n"
        text += "3️⃣ Получите подтверждение"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    
    except (ValueError, User.DoesNotExist) as e:
        bot.answer_callback_query(call.id, "Ошибка обработки")


def check_payment(call: CallbackQuery) -> None:
    """Проверяет статус оплаты и обрабатывает успешные платежи"""
    try:
        # Парсим callback_data: check_payment_{payment_id}_{month}_{year}
        parts = call.data.split('_')
        if len(parts) != 5:
            bot.answer_callback_query(call.id, "Ошибка в данных")
            return
        
        payment_id = parts[2]
        month = int(parts[3])
        year = int(parts[4])
        
        user = User.objects.get(telegram_id=str(call.from_user.id))
        
        # Проверяем, не оплачен ли уже этот месяц
        if PaymentHistory.is_month_paid(user, month, year):
            bot.answer_callback_query(call.id, f"Месяц {MONTH_NAMES[month]} {year} уже оплачен!")
            return
        
        # Получаем информацию о платеже из ЮKassa
        yookassa_client = YooKassaClient()
        payment_info = yookassa_client.get_payment(payment_id)
        
        if not payment_info:
            bot.answer_callback_query(call.id, "Ошибка получения информации о платеже")
            return
        
        payment_status = payment_info.get('status')
        
        if payment_status == 'succeeded':
            # Платеж успешен - обновляем базу данных
            try:
                payment = Payment.objects.get(yookassa_payment_id=payment_id)
                payment.status = 'succeeded'
                payment.payment_method = payment_info.get('payment_method', {})
                payment.save()
                
                # Создаем запись в истории оплат
                PaymentHistory.objects.create(
                    user=user,
                    payment=payment,
                    month=month,
                    year=year,
                    amount_paid=payment.amount,
                    pricing_plan=payment.pricing_plan
                )
                
                # Уведомляем пользователя об успешной оплате
                notify_payment_success(user.telegram_id, month, year, payment.amount)
                
                # Уведомляем всех администраторов
                notify_admins_about_payment(user, month, year, payment.amount)
                
                # Обновляем сообщение
                text = f"🎉 Оплата подтверждена!\n\n"
                text += f"💰 Сумма: {payment.amount} руб.\n"
                text += f"📅 Месяц: {MONTH_NAMES[month]} {year}\n"
                text += f"✅ Теперь вы можете посещать занятия в этом месяце!"
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    text=text,
                    reply_markup=generate_payment_menu_keyboard(),
                    message_id=call.message.message_id
                )
                
            except Payment.DoesNotExist:
                bot.answer_callback_query(call.id, "Платеж не найден в базе данных")
                return
                
        elif payment_status == 'pending':
            bot.answer_callback_query(call.id, "Платеж еще не завершен. Попробуйте позже.")
        elif payment_status == 'canceled':
            bot.answer_callback_query(call.id, "Платеж отменен.")
        else:
            bot.answer_callback_query(call.id, f"Статус платежа: {payment_status}")
    
    except (ValueError, User.DoesNotExist) as e:
        bot.answer_callback_query(call.id, "Ошибка обработки")


def payment_history(call: CallbackQuery) -> None:
    """Показывает историю платежей пользователя"""
    try:
        user = User.objects.get(telegram_id=str(call.from_user.id))
        
        # Получаем историю оплаченных месяцев
        history = PaymentHistory.objects.filter(user=user).order_by('-year', '-month')
        
        text = "📊 История оплат\n\n"
        
        if history.exists():
            for record in history:
                month_name = MONTH_NAMES[record.month]
                text += f"✅ {month_name} {record.year} - {record.amount_paid} руб.\n"
                text += f"   📅 Оплачено: {record.paid_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        else:
            text += "Платежей пока нет."
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=UNIVERSAL_BUTTONS,
            message_id=call.message.message_id
        )
    
    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "Пользователь не найден")


def notify_payment_success(user_telegram_id: str, month: int, year: int, amount: Decimal):
    """Уведомляет пользователя об успешной оплате"""
    try:
        text = f"🎉 Оплата прошла успешно!\n\n"
        text += f"💰 Сумма: {amount} руб.\n"
        text += f"📅 Оплачен месяц: {MONTH_NAMES[month]} {year}\n"
        text += f"✅ Теперь вы можете посещать занятия в этом месяце!"
        
        bot.send_message(
            chat_id=user_telegram_id,
            text=text,
            reply_markup=generate_payment_menu_keyboard()
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления: {e}")


def notify_admins_about_payment(user: User, month: int, year: int, amount: Decimal):
    """Уведомляет всех администраторов о новой оплате"""
    try:
        # Получаем всех администраторов
        admins = User.objects.filter(is_admin=True)
        
        if not admins.exists():
            return
        
        text = f"💰 Новая оплата!\n\n"
        text += f"👤 Ученик: {user.full_name}\n"
        text += f"🆔 Telegram ID: {user.telegram_id}\n"
        text += f"📚 Класс: {user.course_or_class}\n"
        text += f"📅 Месяц: {MONTH_NAMES[month]} {year}\n"
        text += f"💰 Сумма: {amount} руб.\n"
        text += f"⏰ Время: {timezone.now().strftime('%d.%m.%Y %H:%M')}"
        
        # Отправляем уведомление каждому администратору
        for admin in admins:
            try:
                bot.send_message(
                    chat_id=admin.telegram_id,
                    text=text
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления администратору {admin.telegram_id}: {e}")
                
    except Exception as e:
        print(f"Ошибка при уведомлении администраторов: {e}") 