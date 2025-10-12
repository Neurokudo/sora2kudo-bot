"""
🌍 Мультиязычная система для SORA 2 от Neurokudo
Поддержка 5 языков: Русский, Английский, Испанский, Арабский, Хинди
"""

LANG = {
    "ru": {
        # Основные сообщения
        "welcome": "👋 Привет, {name}! Это <b>SORA 2 от Neurokudo</b>.\n\n🎬 <b>Твой тариф:</b> {plan}\n🎞 <b>Осталось видео:</b> {videos_left}\n\n🔥 <b>Создавай крутые вирусные видео и радуй друзей и подписчиков!</b>\n\n💡 <b>Выбери действие:</b>",
        "choose_action": "💡 <b>Выбери действие:</b>",
        "choose_language": "🌍 <b>Выберите язык:</b>",
        "lang_selected": "✅ <b>Язык изменён на Русский.</b>",
        "help": "Опиши свою идею — и я помогу превратить её в видео.",
        
        # Меню и кнопки
        "btn_create_video": "🎬 Создать видео",
        "btn_examples": "📘 Примеры", 
        "btn_profile": "💰 Кабинет",
        "btn_help": "❓ Помощь",
        "btn_language": "🌍 Язык",
        
        # Ориентация видео
        "choose_orientation": "📐 <b>Выбери ориентацию для будущих видео:</b>",
        "orientation_vertical": "📱 Вертикальное",
        "orientation_horizontal": "🖥 Горизонтальное",
        "orientation_selected": "✅ <b>Выбрана {orientation} ориентация</b>\n\n🎬 <b>Опиши сцену простыми словами:</b>\nКто в кадре, где происходит действие, что они делают, какая атмосфера и погода.\nДобавь, если нужно, детали: одежду, эмоции, свет, фон.\n\n📸 <b>Пример:</b>\n<code>Рыбаки в лодке поймали русалку, один в тельняшке тянет сеть, русалка шипит и вырывается, съёмка на телефон, вода мутная, туман.</code>",
        "orientation_vertical_name": "вертикальная",
        "orientation_horizontal_name": "горизонтальная",
        
        # Создание видео
        "create_video": "🎬 <b>Создание видео</b>\n\n📐 Ориентация: <b>{orientation}</b>\n🎞 Осталось видео: <b>{videos_left}</b>\n\n✏️ <b>Опиши сцену простыми словами:</b>\nКто в кадре, где происходит действие, что они делают, какая атмосфера и погода.\nДобавь, если нужно, детали: одежду, эмоции, свет, фон.\n\n📸 <b>Пример:</b>\n<code>Рыбаки в лодке поймали русалку, один в тельняшке тянет сеть, русалка шипит и вырывается, съёмка на телефон, вода мутная, туман.</code>",
        "video_accepted": "🎬 <b>Принято описание!</b>\n\n📝 <b>Описание:</b> {description}\n📐 <b>Ориентация:</b> {orientation}\n🎞 <b>Осталось видео:</b> {videos_left}\n\n⏳ <b>Ваше видео создается, ожидайте...</b>",
        "video_ready": "🎉 <b>Ваше видео готово!</b>\n\n🎬 Видео успешно создано через Sora 2\n🎞 Осталось видео: <b>{videos_left}</b>\n\n💡 Для продолжения создания пришлите новое описание!",
        "no_videos_left": "🚫 <b>У тебя закончились видео!</b>\n\n💳 Купи новый тариф в <b>💰 Кабинет</b>",
        
        # Примеры
        "examples": "📘 <b>Примеры идей для видео:</b>\n\n🔹 Рыбаки вытаскивают сеть, в ней странное существо\n🔹 Грибники находят движущуюся массу под листьями\n🔹 Бабушка кормит капибару у окна, рассвет\n🔹 Советские рабочие открывают капсулу времени\n🔹 Дети находят портал в другой мир\n🔹 Старый дом с привидениями, ночь\n\n💡 <b>Теперь создавай свое видео!</b>",
        
        # Профиль
        "profile": "💰 <b>Твой кабинет</b>\n\n👤 Имя: <b>{name}</b>\n📦 Тариф: <b>{plan}</b>\n🎞 Осталось видео: <b>{videos_left}</b>\n💳 Всего оплачено: <b>{payments} ₽</b>\n📅 Регистрация: <b>{date}</b>\n\n🔁 <b>Нужно больше видео?</b>\nВыбери тариф:",
        
        # Помощь
        "help_text": "🧭 <b>Помощь</b>\n\nОпиши свою проблему, я постараюсь помочь скоро!",
        "support_sent": "✅ Сообщение отправлено. Я постараюсь ответить как можно скорее!",
        
        # Кнопки покупки тарифов
        "btn_buy_trial": "🐣 Купить Пробный (₽490)",
        "btn_buy_basic": "🎬 Купить Базовый (₽1 290)", 
        "btn_buy_maximum": "🚀 Купить Максимум (₽2 990)",
        "btn_buy_foreign": "💳 Иностранная карта",
        "btn_buy_tariff": "💳 Купить тариф",
        "tariff_selection": "💳 <b>Выберите тариф для покупки:</b>",
        
        # Сообщения для пользователей без тарифа
        "no_tariff_message": "🚀 <b>Начни создавать вирусные видео прямо сейчас!</b>\n\n💎 <b>Выбери тариф и получи доступ к SORA 2:</b>\n🐣 <b>Пробный</b> — 3 видео за ₽490\n🎬 <b>Базовый</b> — 10 видео за ₽1 290\n🚀 <b>Максимум</b> — 30 видео за ₽2 990\n\n🔥 <b>Создавай крутые видео и радуй друзей и подписчиков!</b>",
        
        # Общие фразы
        "use_buttons": "💡 Используй кнопки меню или выбери ориентацию видео!",
        "error_restart": "❌ Ошибка. Попробуй /start",
        "error_getting_data": "❌ Ошибка получения данных. Попробуй /start",
    },
    
    "en": {
        # Основные сообщения
        "welcome": "👋 Hi, {name}! This is <b>SORA 2 by Neurokudo</b>.\n\n🎬 <b>Your tariff:</b> {plan}\n🎞 <b>Videos left:</b> {videos_left}\n\n🔥 <b>Create amazing viral videos and delight your friends and followers!</b>\n\n💡 <b>Choose an action:</b>",
        "choose_action": "💡 <b>Choose an action:</b>",
        "choose_language": "🌍 <b>Choose your language:</b>",
        "lang_selected": "✅ <b>Language set to English.</b>",
        "help": "Describe your idea — and I'll help turn it into a video.",
        
        # Меню и кнопки
        "btn_create_video": "🎬 Create Video",
        "btn_examples": "📘 Examples", 
        "btn_profile": "💰 Profile",
        "btn_help": "❓ Help",
        "btn_language": "🌍 Language",
        
        # Ориентация видео
        "choose_orientation": "📐 <b>Choose orientation for future videos:</b>",
        "orientation_vertical": "📱 Vertical",
        "orientation_horizontal": "🖥 Horizontal",
        "orientation_selected": "✅ <b>{orientation} orientation selected</b>\n\n🎬 <b>Describe the scene in simple words:</b>\nWho is in the frame, where the action takes place, what they are doing, atmosphere and weather.\nAdd details if needed: clothing, emotions, lighting, background.\n\n📸 <b>Example:</b>\n<code>Fishermen in a boat caught a mermaid, one in a striped shirt pulls the net, mermaid hisses and breaks free, phone recording, murky water, fog.</code>",
        "orientation_vertical_name": "vertical",
        "orientation_horizontal_name": "horizontal",
        
        # Создание видео
        "create_video": "🎬 <b>Creating Video</b>\n\n📐 Orientation: <b>{orientation}</b>\n🎞 Videos left: <b>{videos_left}</b>\n\n✏️ <b>Describe the scene in simple words:</b>\nWho is in the frame, where the action takes place, what they are doing, atmosphere and weather.\nAdd details if needed: clothing, emotions, lighting, background.\n\n📸 <b>Example:</b>\n<code>Fishermen in a boat caught a mermaid, one in a striped shirt pulls the net, mermaid hisses and breaks free, phone recording, murky water, fog.</code>",
        "video_accepted": "🎬 <b>Description accepted!</b>\n\n📝 <b>Description:</b> {description}\n📐 <b>Orientation:</b> {orientation}\n🎞 <b>Videos left:</b> {videos_left}\n\n⏳ <b>Your video is being created, please wait...</b>",
        "video_ready": "🎉 <b>Your video is ready!</b>\n\n🎬 Video successfully created via Sora 2\n🎞 Videos left: <b>{videos_left}</b>\n\n💡 To continue creating, send a new description!",
        "no_videos_left": "🚫 <b>You're out of videos!</b>\n\n💳 Buy a new package in <b>💰 Profile</b>",
        
        # Примеры
        "examples": "📘 <b>Video idea examples:</b>\n\n🔹 Fishermen pulling a net with strange creature\n🔹 Mushroom pickers find moving mass under leaves\n🔹 Grandma feeding capybara by window at dawn\n🔹 Soviet workers opening time capsule\n🔹 Children finding portal to another world\n🔹 Old haunted house at night\n\n💡 <b>Now create your video!</b>",
        
        # Профиль
        "profile": "💰 <b>Your Profile</b>\n\n👤 Name: <b>{name}</b>\n📦 Plan: <b>{plan}</b>\n🎞 Videos left: <b>{videos_left}</b>\n💳 Total paid: <b>{payments} ₽</b>\n📅 Registration: <b>{date}</b>\n\n🔁 <b>Need more videos?</b>\nChoose package:\n🐣 Trial — 3 videos → ₽490\n🎬 Basic — 10 videos → ₽1,290\n🚀 Max — 30 videos → ₽2,990",
        
        # Помощь
        "help_text": "🧭 <b>Help</b>\n\nDescribe your problem, I'll try to help soon!",
        "support_sent": "✅ Message sent. I'll try to respond as soon as possible!",
        
        # Кнопки покупки тарифов
        "btn_buy_trial": "🐣 Buy Trial (₽490)",
        "btn_buy_basic": "🎬 Buy Basic (₽1 290)", 
        "btn_buy_maximum": "🚀 Buy Maximum (₽2 990)",
        "btn_buy_foreign": "💳 Foreign Card",
        "btn_buy_tariff": "💳 Buy tariff",
        "tariff_selection": "💳 <b>Choose tariff to purchase:</b>",
        
        # Сообщения для пользователей без тарифа
        "no_tariff_message": "🚀 <b>Start creating viral videos right now!</b>\n\n💎 <b>Choose a tariff and get access to SORA 2:</b>\n🐣 <b>Trial</b> — 3 videos for ₽490\n🎬 <b>Basic</b> — 10 videos for ₽1 290\n🚀 <b>Maximum</b> — 30 videos for ₽2 990\n\n🔥 <b>Create amazing videos and delight your friends and followers!</b>",
        
        # Общие фразы
        "use_buttons": "💡 Use menu buttons or choose video orientation!",
        "error_restart": "❌ Error. Try /start",
        "error_getting_data": "❌ Error getting data. Try /start",
    },
    
    "es": {
        # Основные сообщения
        "welcome": "👋 ¡Hola, {name}! Este es <b>SORA 2 de Neurokudo</b>.\n\n🎬 <b>Tu plan:</b> {plan}\n🎞 <b>Videos restantes:</b> {videos_left}\n\nAquí puedes crear videos desde descripciones — solo escribe lo que quieres filmar.\n\n💡 <b>Elige una acción:</b>",
        "choose_action": "💡 <b>Elige una acción:</b>",
        "choose_language": "🌍 <b>Elige tu idioma:</b>",
        "lang_selected": "✅ <b>Idioma cambiado a Español.</b>",
        "help": "Describe tu idea y la convertiré en video.",
        
        # Меню и кнопки
        "btn_create_video": "🎬 Crear Video",
        "btn_examples": "📘 Ejemplos", 
        "btn_profile": "💰 Perfil",
        "btn_help": "❓ Ayuda",
        "btn_language": "🌍 Idioma",
        
        # Ориентация видео
        "choose_orientation": "📐 <b>Elige orientación para futuros videos:</b>",
        "orientation_vertical": "📱 Vertical",
        "orientation_horizontal": "🖥 Horizontal",
        "orientation_selected": "✅ <b>Orientación {orientation} seleccionada</b>\n\n¡Ahora presiona <b>🎬 Crear Video</b> y describe lo que quieres filmar!",
        "orientation_vertical_name": "vertical",
        "orientation_horizontal_name": "horizontal",
        
        # Создание видео
        "create_video": "🎬 <b>Creando Video</b>\n\n📐 Orientación: <b>{orientation}</b>\n🎞 Videos restantes: <b>{videos_left}</b>\n\n✏️ <b>Describe lo que quieres filmar:</b>\nEjemplo: <code>Pescadores sacando red con sirena adentro</code>",
        "video_accepted": "🎬 <b>¡Descripción aceptada!</b>\n\n📝 <b>Descripción:</b> {description}\n📐 <b>Orientación:</b> {orientation}\n🎞 <b>Videos restantes:</b> {videos_left}\n\n⏳ Video siendo creado via Sora 2...\n📨 ¡El resultado será enviado aquí!",
        "no_videos_left": "🚫 <b>¡Te quedaste sin videos!</b>\n\n💳 Compra nuevo paquete en <b>💰 Perfil</b>",
        
        # Примеры
        "examples": "📘 <b>Ejemplos de ideas para video:</b>\n\n🔹 Pescadores sacando red con criatura extraña\n🔹 Recolectores de hongos encuentran masa móvil bajo hojas\n🔹 Abuela alimentando capibara en ventana al amanecer\n🔹 Trabajadores soviéticos abriendo cápsula del tiempo\n🔹 Niños encontrando portal a otro mundo\n🔹 Casa embrujada vieja en la noche\n\n💡 <b>¡Ahora crea tu video!</b>",
        
        # Профиль
        "profile": "💰 <b>Tu Perfil</b>\n\n👤 Nombre: <b>{name}</b>\n📦 Plan: <b>{plan}</b>\n🎞 Videos restantes: <b>{videos_left}</b>\n💳 Total pagado: <b>{payments} ₽</b>\n📅 Registro: <b>{date}</b>\n\n🔁 <b>¿Necesitas más videos?</b>\nElige paquete:\n🐣 Prueba — 3 videos → ₽490\n🎬 Básico — 10 videos → ₽1,290\n🚀 Máximo — 30 videos → ₽2,990",
        
        # Помощь
        "help_text": "🧭 <b>Ayuda</b>\n\nDescribe tu problema, ¡trataré de ayudar pronto!",
        "support_sent": "✅ Mensaje enviado. ¡Trataré de responder lo antes posible!",
        
        # Общие фразы
        "use_buttons": "💡 ¡Usa botones del menú o elige orientación de video!",
        "error_restart": "❌ Error. Prueba /start",
        "error_getting_data": "❌ Error obteniendo datos. Prueba /start",
    },
    
    "ar": {
        # Основные сообщения
        "welcome": "👋 مرحباً {name}! هذا هو <b>SORA 2 من Neurokudo</b>.\n\n🎬 <b>خطتك:</b> {plan}\n🎞 <b>الفيديوهات المتبقية:</b> {videos_left}\n\nهنا يمكنك إنشاء فيديوهات من الوصف — فقط اكتب ما تريد تصويره.\n\n💡 <b>اختر إجراء:</b>",
        "choose_action": "💡 <b>اختر إجراء:</b>",
        "choose_language": "🌍 <b>اختر لغتك:</b>",
        "lang_selected": "✅ <b>تم تغيير اللغة إلى العربية.</b>",
        "help": "صف فكرتك وسأحولها إلى فيديو.",
        
        # Меню и кнопки
        "btn_create_video": "🎬 إنشاء فيديو",
        "btn_examples": "📘 أمثلة", 
        "btn_profile": "💰 الملف الشخصي",
        "btn_help": "❓ مساعدة",
        "btn_language": "🌍 اللغة",
        
        # Ориентация видео
        "choose_orientation": "📐 <b>اختر اتجاه الفيديوهات المستقبلية:</b>",
        "orientation_vertical": "📱 عمودي",
        "orientation_horizontal": "🖥 أفقي",
        "orientation_selected": "✅ <b>تم اختيار الاتجاه {orientation}</b>\n\nالآن اضغط <b>🎬 إنشاء فيديو</b> وصف ما تريد تصويره!",
        "orientation_vertical_name": "عمودي",
        "orientation_horizontal_name": "أفقي",
        
        # Создание видео
        "create_video": "🎬 <b>إنشاء فيديو</b>\n\n📐 الاتجاه: <b>{orientation}</b>\n🎞 الفيديوهات المتبقية: <b>{videos_left}</b>\n\n✏️ <b>صف ما تريد تصويره:</b>\nمثال: <code>صيادون يسحبون شبكة بها حورية</code>",
        "video_accepted": "🎬 <b>تم قبول الوصف!</b>\n\n📝 <b>الوصف:</b> {description}\n📐 <b>الاتجاه:</b> {orientation}\n🎞 <b>الفيديوهات المتبقية:</b> {videos_left}\n\n⏳ يتم إنشاء الفيديو عبر Sora 2...\n📨 ستتم إرسال النتيجة هنا!",
        "no_videos_left": "🚫 <b>انتهت فيديوهاتك!</b>\n\n💳 اشتر باقة جديدة في <b>💰 الملف الشخصي</b>",
        
        # Примеры
        "examples": "📘 <b>أمثلة أفكار للفيديو:</b>\n\n🔹 صيادون يسحبون شبكة بها مخلوق غريب\n🔹 جامعو الفطر يجدون كتلة متحركة تحت الأوراق\n🔹 جدة تطعم كابيبارا عند النافذة في الفجر\n🔹 عمال سوفييت يفتحون كبسولة زمنية\n🔹 أطفال يجدون بوابة لعالم آخر\n🔹 منزل مسكون قديم في الليل\n\n💡 <b>الآن أنشئ فيديوك!</b>",
        
        # Профиль
        "profile": "💰 <b>ملفك الشخصي</b>\n\n👤 الاسم: <b>{name}</b>\n📦 الخطة: <b>{plan}</b>\n🎞 الفيديوهات المتبقية: <b>{videos_left}</b>\n💳 إجمالي المدفوع: <b>{payments} ₽</b>\n📅 التسجيل: <b>{date}</b>\n\n🔁 <b>تحتاج فيديوهات أكثر؟</b>\nاختر باقة:\n🐣 تجريبية — 3 فيديوهات → ₽490\n🎬 أساسية — 10 فيديوهات → ₽1,290\n🚀 قصوى — 30 فيديو → ₽2,990",
        
        # Помощь
        "help_text": "🧭 <b>مساعدة</b>\n\nصف مشكلتك، سأحاول المساعدة قريباً!",
        "support_sent": "✅ تم إرسال الرسالة. سأحاول الرد في أقرب وقت ممكن!",
        
        # Общие фразы
        "use_buttons": "💡 استخدم أزرار القائمة أو اختر اتجاه الفيديو!",
        "error_restart": "❌ خطأ. جرب /start",
        "error_getting_data": "❌ خطأ في الحصول على البيانات. جرب /start",
    },
    
    "hi": {
        # Основные сообщения
        "welcome": "👋 नमस्ते {name}! यह है <b>SORA 2 by Neurokudo</b>।\n\n🎬 <b>आपकी योजना:</b> {plan}\n🎞 <b>बचे वीडियो:</b> {videos_left}\n\nयहाँ आप विवरण से वीडियो बना सकते हैं — बस लिखें कि आप क्या फिल्माना चाहते हैं।\n\n💡 <b>एक क्रिया चुनें:</b>",
        "choose_action": "💡 <b>एक क्रिया चुनें:</b>",
        "choose_language": "🌍 <b>अपनी भाषा चुनें:</b>",
        "lang_selected": "✅ <b>भाषा हिंदी में बदल दी गई है।</b>",
        "help": "अपना विचार बताओ — मैं उसे वीडियो में बदल दूँगा।",
        
        # Меню и кнопки
        "btn_create_video": "🎬 वीडियो बनाएं",
        "btn_examples": "📘 उदाहरण", 
        "btn_profile": "💰 प्रोफाइल",
        "btn_help": "❓ मदद",
        "btn_language": "🌍 भाषा",
        
        # Ориентация видео
        "choose_orientation": "📐 <b>भविष्य के वीडियो के लिए दिशा चुनें:</b>",
        "orientation_vertical": "📱 खड़ा",
        "orientation_horizontal": "🖥 लेटा",
        "orientation_selected": "✅ <b>{orientation} दिशा चुनी गई</b>\n\nअब <b>🎬 वीडियो बनाएं</b> दबाएं और बताएं कि आप क्या फिल्माना चाहते हैं!",
        "orientation_vertical_name": "खड़ी",
        "orientation_horizontal_name": "लेटी",
        
        # Создание видео
        "create_video": "🎬 <b>वीडियो बना रहे हैं</b>\n\n📐 दिशा: <b>{orientation}</b>\n🎞 बचे वीडियो: <b>{videos_left}</b>\n\n✏️ <b>बताएं कि आप क्या फिल्माना चाहते हैं:</b>\nउदाहरण: <code>मछुआरे जाल खींच रहे हैं जिसमें राक्षसी है</code>",
        "video_accepted": "🎬 <b>विवरण स्वीकार किया गया!</b>\n\n📝 <b>विवरण:</b> {description}\n📐 <b>दिशा:</b> {orientation}\n🎞 <b>बचे वीडियो:</b> {videos_left}\n\n⏳ Sora 2 के माध्यम से वीडियो बनाया जा रहा है...\n📨 परिणाम यहाँ भेजा जाएगा!",
        "no_videos_left": "🚫 <b>आपके वीडियो खत्म हो गए!</b>\n\n💳 <b>💰 प्रोफाइल</b> में नया पैकेज खरीदें",
        
        # Примеры
        "examples": "📘 <b>वीडियो आइडिया उदाहरण:</b>\n\n🔹 मछुआरे जाल खींच रहे हैं जिसमें अजीब जीव है\n🔹 मशरूम बीनने वाले पत्तों के नीचे हिलती हुई चीज़ पाते हैं\n🔹 दादी सुबह खिड़की पर कैपिबारा को खाना खिला रही हैं\n🔹 सोवियत कर्मचारी समय कैप्सूल खोल रहे हैं\n🔹 बच्चे दूसरी दुनिया का पोर्टल पाते हैं\n🔹 रात में पुराना भूतिया घर\n\n💡 <b>अब अपना वीडियो बनाएं!</b>",
        
        # Профиль
        "profile": "💰 <b>आपका प्रोफाइल</b>\n\n👤 नाम: <b>{name}</b>\n📦 योजना: <b>{plan}</b>\n🎞 बचे वीडियो: <b>{videos_left}</b>\n💳 कुल भुगतान: <b>{payments} ₽</b>\n📅 पंजीकरण: <b>{date}</b>\n\n🔁 <b>और वीडियो चाहिए?</b>\nपैकेज चुनें:\n🐣 ट्रायल — 3 वीडियो → ₽490\n🎬 बेसिक — 10 वीडियो → ₽1,290\n🚀 मैक्स — 30 वीडियो → ₽2,990",
        
        # Помощь
        "help_text": "🧭 <b>मदद</b>\n\nअपनी समस्या बताएं, मैं जल्दी मदद करने की कोशिश करूंगा!",
        "support_sent": "✅ संदेश भेजा गया। मैं जल्द से जल्द जवाब देने की कोशिश करूंगा!",
        
        # Общие фразы
        "use_buttons": "💡 मेनू बटन का उपयोग करें या वीडियो दिशा चुनें!",
        "error_restart": "❌ त्रुटि। /start आज़माएं",
        "error_getting_data": "❌ डेटा प्राप्त करने में त्रुटि। /start आज़माएं",
    },
}

# Языковые коды и флаги для кнопок
LANGUAGE_BUTTONS = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English", 
    "es": "🇪🇸 Español",
    "ar": "🇸🇦 العربية",
    "hi": "🇮🇳 हिन्दी"
}

def get_text(language: str, key: str, **kwargs) -> str:
    """Получение переведенного текста"""
    if language not in LANG:
        language = "en"
    
    if key not in LANG[language]:
        # Fallback на английский
        if key in LANG["en"]:
            return LANG["en"][key].format(**kwargs)
        return key
    
    return LANG[language][key].format(**kwargs)

def is_rtl_language(language: str) -> bool:
    """Проверка, является ли язык RTL (справа налево)"""
    return language == "ar"
