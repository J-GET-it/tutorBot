# Конфигурация цен для разных классов обучения

PRICING_CONFIG = {
    # ОГЭ и основные классы
    'oge_9': {
        'name': '💯ОГЭ(9 класс)',
        'price': 5650,
        'description': '2 часа / 1 раз в неделю',
        'keywords': ['9', 'oge', 'огэ', '9 класс']
    },
    'ege_base': {
        'name': '💯ЕГЭ База',
        'price': 5650,
        'description': '2 часа / 1 раз в неделю',
        'keywords': ['егэ база', 'ege base', 'база']
    },
    'class_7': {
        'name': '💯7 класс',
        'price': 5650,
        'description': '2 часа / 1 раз в неделю',
        'keywords': ['7', '7 класс']
    },
    'class_8': {
        'name': '💯8 класс (Алгебра + Геометрия)',
        'price': 5650,
        'description': '2 часа / 1 раз в неделю',
        'keywords': ['8', '8 класс']
    },
    
    # ЕГЭ Профиль
    'ege_profile': {
        'name': '💯ЕГЭ Профиль 11 класс',
        'price': 7900,
        'description': '4 часа в неделю + дом.задания + возможно Zoom онлайн занятие 1 раз/неделю',
        'keywords': ['11', '11 класс', 'егэ профиль', 'ege profile', 'профиль']
    },
    
    # 10 класс
    'class_10': {
        'name': '💯10 класс',
        'price': 7000,
        'description': '3 часа в неделю',
        'keywords': ['10', '10 класс']
    },
    
    # Младшие классы
    'class_5_6': {
        'name': '💯5, 6 класс',
        'price': 3670,
        'description': '1 час / 1 раз в неделю',
        'keywords': ['5', '6', '5 класс', '6 класс']
    },
    
    # ВУЗ курсы (стоимость 1 рубль)
    'university_course_1': {
        'name': '🎓1 курс ВУЗа',
        'price': 1,
        'description': 'Студент 1 курса ВУЗа',
        'keywords': ['1 курс', 'course_1', '1']
    },
    'university_course_2': {
        'name': '🎓2 курс ВУЗа',
        'price': 1,
        'description': 'Студент 2 курса ВУЗа',
        'keywords': ['2 курс', 'course_2', '2']
    },
    'university_course_3': {
        'name': '🎓3 курс ВУЗа',
        'price': 1,
        'description': 'Студент 3 курса ВУЗа',
        'keywords': ['3 курс', 'course_3', '3']
    },
    'university_course_4': {
        'name': '🎓4 курс ВУЗа',
        'price': 1,
        'description': 'Студент 4 курса ВУЗа',
        'keywords': ['4 курс', 'course_4', '4']
    },
    'university_course_5': {
        'name': '🎓5 курс ВУЗа',
        'price': 1,
        'description': 'Студент 5 курса ВУЗа',
        'keywords': ['5 курс', 'course_5', '5']
    },
    'university_course_6': {
        'name': '🎓6 курс ВУЗа',
        'price': 1,
        'description': 'Студент 6 курса ВУЗа',
        'keywords': ['6 курс', 'course_6', '6']
    }
}

def get_price_by_class(class_info):
    """
    Получить цену по информации о классе пользователя
    
    Args:
        class_info (str): Информация о классе/курсе пользователя
    
    Returns:
        dict: Словарь с информацией о цене или None если не найдено
    """
    if not class_info:
        return None
    
    class_info_lower = class_info.lower().strip()
    
    for price_key, price_data in PRICING_CONFIG.items():
        for keyword in price_data['keywords']:
            if keyword in class_info_lower:
                return {
                    'key': price_key,
                    'name': price_data['name'],
                    'price': price_data['price'],
                    'description': price_data['description']
                }
    
    return None

def get_all_price_options():
    """
    Получить все доступные варианты цен
    
    Returns:
        list: Список всех ценовых планов
    """
    return [
        {
            'key': key,
            'name': data['name'],
            'price': data['price'],
            'description': data['description']
        }
        for key, data in PRICING_CONFIG.items()
    ]

# Конфигурация цен для разных классов обучения 
