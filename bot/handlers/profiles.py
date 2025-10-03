from django.db import transaction
from telebot.types import CallbackQuery, Message
from bot import bot
from bot.models import User, StudentProfile
from bot.keyboards import (
    generate_profiles_menu_keyboard,
    generate_profiles_list_keyboard,
    generate_profile_management_keyboard,
    generate_profile_data_management_keyboard,
    generate_profile_school_classes_keyboard,
    generate_profile_confirmation_keyboard,
    generate_profile_deletion_confirmation_keyboard,
    generate_profile_deletion_final_confirmation_keyboard,
    UNIVERSAL_BUTTONS
)
from bot.texts import (
    PROFILES_MENU_TEXT,
    PROFILES_LIST_TEXT,
    PROFILE_INFO_TEXT,
    PROFILE_DATA_MANAGEMENT_TEXT,
    PROFILE_CREATION_WELCOME,
    PROFILE_CLASS_CHOICE,
    PROFILE_CONFIRMATION,
    PROFILE_CREATED_SUCCESS,
    PROFILE_DELETION_CONFIRMATION,
    PROFILE_DELETION_FINAL_CONFIRMATION,
    PROFILE_DELETED_SUCCESS,
    PROFILE_SWITCHED_SUCCESS,
    NO_PROFILES_TEXT,
    PROFILE_ALREADY_EXISTS
)

# Словарь для хранения состояния создания профиля
profile_creation_states = {}


def profiles_menu(call: CallbackQuery) -> None:
    """Показывает меню управления профилями"""
    try:
        user = User.objects.get(telegram_id=str(call.from_user.id))
        
        text = PROFILES_MENU_TEXT
        markup = generate_profiles_menu_keyboard()
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "Пользователь не найден")


def view_profiles(call: CallbackQuery) -> None:
    """Показывает список профилей пользователя с информацией об активном профиле"""
    try:
        user = User.objects.get(telegram_id=str(call.from_user.id))
        profiles = user.student_profiles.all().order_by('-is_active', 'created_at')
        
        if not profiles.exists():
            text = NO_PROFILES_TEXT
            markup = generate_profiles_menu_keyboard()
        else:
            # Получаем активный профиль
            active_profile = get_active_profile(user)
            
            text = f"👥 Ваши профили\n\n"
            
            if active_profile:
                text += f"✅ **Активный профиль:**\n"
                text += f"👤 {active_profile.profile_name}\n"
                text += f"📚 {active_profile.class_number} класс\n"
                text += f"📊 Уровень: {active_profile.get_education_level_display() or 'Не указан'}\n"
                text += f"💰 Баланс: {active_profile.balance} ₽\n\n"
                text += f"Выберите профиль для управления:\n"
            else:
                text += f"❌ У вас нет активного профиля\n\n"
                text += f"Выберите профиль для управления:\n"
            
            markup = generate_profiles_list_keyboard(profiles)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "Пользователь не найден")


def create_profile(call: CallbackQuery) -> None:
    """Начинает процесс создания нового профиля"""
    try:
        user = User.objects.get(telegram_id=str(call.from_user.id))
        
        # Устанавливаем состояние создания профиля
        profile_creation_states[str(call.from_user.id)] = {
            'step': 'waiting_profile_name',
            'user_id': user.telegram_id
        }
        
        text = PROFILE_CREATION_WELCOME
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=UNIVERSAL_BUTTONS,
            message_id=call.message.message_id
        )
    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "Пользователь не найден")


def handle_profile_creation_message(message: Message) -> None:
    """Обрабатывает текстовые сообщения во время создания профиля"""
    telegram_id = str(message.from_user.id)
    
    if telegram_id not in profile_creation_states:
        return
    
    state = profile_creation_states[telegram_id]
    
    if state['step'] == 'waiting_profile_name':
        # Сохраняем имя профиля и переходим к следующему шагу
        profile_name = message.text.strip()
        if len(profile_name) < 2:
            bot.send_message(message.chat.id, "Пожалуйста, введите корректное имя профиля (минимум 2 символа):")
            return
        
        try:
            user = User.objects.get(telegram_id=telegram_id)
            
            # Проверяем, не существует ли уже профиль с таким именем
            if user.student_profiles.filter(profile_name=profile_name).exists():
                bot.send_message(message.chat.id, PROFILE_ALREADY_EXISTS)
                return
            
            # Сохраняем имя профиля в состоянии
            state['profile_name'] = profile_name
            state['step'] = 'waiting_class'
            
            text = PROFILE_CLASS_CHOICE.format(profile_name=profile_name)
            markup = generate_profile_school_classes_keyboard()
            
            bot.send_message(message.chat.id, text, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте еще раз.")
            return


def handle_profile_class_choice(call: CallbackQuery) -> None:
    """Обрабатывает выбор класса для профиля"""
    telegram_id = str(call.from_user.id)
    
    if telegram_id not in profile_creation_states:
        return
    
    state = profile_creation_states[telegram_id]
    
    if state['step'] != 'waiting_class':
        return
    
    raw_value = call.data.replace('profile_class_', '')
    education_level = None
    
    if raw_value == '10_base':
        class_number = '10'
        education_level = 'base'
    elif raw_value == '10_profile':
        class_number = '10'
        education_level = 'profile'
    elif raw_value == '11_base':
        class_number = '11'
        education_level = 'base'
    elif raw_value == '11_profile':
        class_number = '11'
        education_level = 'profile'
    else:
        class_number = raw_value
    
    try:
        state['class_number'] = class_number
        state['education_level'] = education_level
        state['step'] = 'waiting_confirmation'
        
        text = PROFILE_CONFIRMATION.format(
            profile_name=state['profile_name'],
            full_name=state['profile_name'],  # Используем имя профиля как ФИО по умолчанию
            class_number=class_number,
            education_level=education_level or 'Не указан'
        )
        markup = generate_profile_confirmation_keyboard()
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "Произошла ошибка. Попробуйте еще раз.")


def confirm_profile_creation(call: CallbackQuery) -> None:
    """Подтверждает создание профиля"""
    telegram_id = str(call.from_user.id)
    
    if telegram_id not in profile_creation_states:
        return
    
    state = profile_creation_states[telegram_id]
    
    if state['step'] != 'waiting_confirmation':
        return
    
    try:
        with transaction.atomic():
            user = User.objects.get(telegram_id=telegram_id)
            
            # Создаем новый профиль
            profile = StudentProfile.objects.create(
                user=user,
                profile_name=state['profile_name'],
                full_name=state['profile_name'],  # Используем имя профиля как ФИО
                class_number=state['class_number'],
                education_level=state['education_level'],
                is_active=True,
                is_registered=True
            )
            
            # Деактивируем все остальные профили пользователя
            user.student_profiles.exclude(id=profile.id).update(is_active=False)
            
            text = PROFILE_CREATED_SUCCESS.format(
                profile_name=profile.profile_name,
                full_name=profile.full_name,
                class_number=profile.class_number,
                education_level=profile.get_education_level_display() or 'Не указан'
            )
            markup = generate_profiles_menu_keyboard()
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                text=text,
                reply_markup=markup,
                message_id=call.message.message_id
            )
            
            # Удаляем состояние создания профиля
            del profile_creation_states[telegram_id]
            
    except Exception as e:
        bot.answer_callback_query(call.id, "Произошла ошибка при создании профиля")


def select_profile(call: CallbackQuery) -> None:
    """Показывает информацию о выбранном профиле"""
    try:
        # Парсим callback_data: select_profile_{profile_id}
        profile_id = int(call.data.split('_')[2])
        
        profile = StudentProfile.objects.get(id=profile_id, user__telegram_id=str(call.from_user.id))
        
        status_display = "Активный" if profile.is_active else "Неактивный"
        
        text = PROFILE_INFO_TEXT.format(
            profile_name=profile.profile_name,
            full_name=profile.full_name or "Не указано",
            class_number=profile.class_number,
            education_level=profile.get_education_level_display() or 'Не указан',
            balance=profile.balance,
            created_at=profile.created_at.strftime('%d.%m.%Y'),
            status=status_display
        )
        markup = generate_profile_management_keyboard(profile.id)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    except (ValueError, StudentProfile.DoesNotExist):
        bot.answer_callback_query(call.id, "Профиль не найден")


def switch_to_profile(call: CallbackQuery) -> None:
    """Переключает на выбранный профиль"""
    try:
        # Парсим callback_data: switch_to_profile_{profile_id}
        profile_id = int(call.data.split('_')[3])
        
        with transaction.atomic():
            profile = StudentProfile.objects.get(id=profile_id, user__telegram_id=str(call.from_user.id))
            
            # Деактивируем все профили пользователя
            profile.user.student_profiles.update(is_active=False)
            
            # Активируем выбранный профиль
            profile.is_active = True
            profile.save()
            
            text = PROFILE_SWITCHED_SUCCESS.format(profile_name=profile.profile_name)
            markup = generate_profiles_menu_keyboard()
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                text=text,
                reply_markup=markup,
                message_id=call.message.message_id
            )
    except (ValueError, StudentProfile.DoesNotExist):
        bot.answer_callback_query(call.id, "Профиль не найден")


def edit_profile_data(call: CallbackQuery) -> None:
    """Показывает меню управления данными профиля"""
    try:
        # Парсим callback_data: edit_profile_data_{profile_id}
        profile_id = int(call.data.split('_')[3])
        
        profile = StudentProfile.objects.get(id=profile_id, user__telegram_id=str(call.from_user.id))
        
        text = PROFILE_DATA_MANAGEMENT_TEXT.format(profile_name=profile.profile_name)
        markup = generate_profile_data_management_keyboard(profile.id)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    except (ValueError, StudentProfile.DoesNotExist):
        bot.answer_callback_query(call.id, "Профиль не найден")


def delete_profile(call: CallbackQuery) -> None:
    """Показывает первое подтверждение удаления профиля"""
    try:
        # Парсим callback_data: delete_profile_{profile_id}
        profile_id = int(call.data.split('_')[2])
        
        profile = StudentProfile.objects.get(id=profile_id, user__telegram_id=str(call.from_user.id))
        
        text = PROFILE_DELETION_CONFIRMATION.format(profile_name=profile.profile_name)
        markup = generate_profile_deletion_confirmation_keyboard(profile.id)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    except (ValueError, StudentProfile.DoesNotExist):
        bot.answer_callback_query(call.id, "Профиль не найден")


def confirm_delete_profile(call: CallbackQuery) -> None:
    """Показывает финальное подтверждение удаления профиля"""
    try:
        # Парсим callback_data: confirm_delete_profile_{profile_id}
        profile_id = int(call.data.split('_')[3])
        
        profile = StudentProfile.objects.get(id=profile_id, user__telegram_id=str(call.from_user.id))
        
        text = PROFILE_DELETION_FINAL_CONFIRMATION.format(
            profile_name=profile.profile_name,
            balance=profile.balance
        )
        markup = generate_profile_deletion_final_confirmation_keyboard(profile.id)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=markup,
            message_id=call.message.message_id
        )
    except (ValueError, StudentProfile.DoesNotExist):
        bot.answer_callback_query(call.id, "Профиль не найден")


def final_delete_profile(call: CallbackQuery) -> None:
    """Выполняет финальное удаление профиля"""
    try:
        # Парсим callback_data: final_delete_profile_{profile_id}
        profile_id = int(call.data.split('_')[3])
        
        with transaction.atomic():
            profile = StudentProfile.objects.get(id=profile_id, user__telegram_id=str(call.from_user.id))
            profile_name = profile.profile_name
            
            # Удаляем профиль
            profile.delete()
            
            text = PROFILE_DELETED_SUCCESS.format(profile_name=profile_name)
            markup = generate_profiles_menu_keyboard()
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                text=text,
                reply_markup=markup,
                message_id=call.message.message_id
            )
    except (ValueError, StudentProfile.DoesNotExist):
        bot.answer_callback_query(call.id, "Профиль не найден")


def is_user_creating_profile(telegram_id: str) -> bool:
    """Проверяет, находится ли пользователь в процессе создания профиля"""
    return str(telegram_id) in profile_creation_states


def get_active_profile(user: User) -> StudentProfile:
    """Получает активный профиль пользователя"""
    try:
        return user.student_profiles.get(is_active=True)
    except StudentProfile.DoesNotExist:
        return None