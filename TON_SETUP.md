# 🚀 Настройка реальных переводов TON

## ✅ Текущий статус
- **WATA платежи**: ✅ Работают
- **Проверка статуса**: ✅ Работает  
- **TON переводы**: 🔥 **ВКЛЮЧЕНЫ! Нужна только настройка кошелька**

## 🔧 Для включения реальных TON переводов:

### 1. ✅ pytoniq уже установлен
Библиотека уже добавлена в `requirements.txt`

### 2. 🔑 Настройте переменные окружения в Railway

**КРИТИЧЕСКИ ВАЖНО:** В Railway Dashboard → Settings → Environment Variables добавьте:

```
SERVICE_WALLET_MNEMONIC=word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13 word14 word15 word16 word17 word18 word19 word20 word21 word22 word23 word24
```

**Где взять мнемоническую фразу:**
- Откройте TONKeeper/Tonhub/TON Wallet
- Перейдите в настройки кошелька `UQAGUqc7XqO7Wc8tH7QGD8LuituUvdGUVccn-SphINODx7xa`
- Скопируйте 24 слова seed фразы
- **ВАЖНО:** Вставьте все 24 слова через пробел в одну строку

### 3. 💰 Пополните сервисный кошелек

Переведите TON на кошелек `UQAGUqc7XqO7Wc8tH7QGD8LuituUvdGUVccn-SphINODx7xa`

**Рекомендуемый баланс:** минимум 10-50 TON для начала работы

### 4. 🚀 Перезапустите Railway

После добавления `SERVICE_WALLET_MNEMONIC` Railway автоматически перезапустится.

## 📊 Что будет в логах при реальных переводах:

```
💸 Sending 0.6047 TON to 0:85d7385590e6be7d41fcc73b308e2e0004311abdcb775b1989f9071112b51d05
🔑 Loading service wallet from mnemonic...
🌐 Connected to TON mainnet
👛 Service wallet loaded: UQAGUqc7XqO7Wc8tH7QGD8LuituUvdGUVccn-SphINODx7xa
💰 Wallet balance: 15.2341 TON
💸 Required amount: 0.6047 TON
🚀 Initiating transfer...
✅ TON transfer completed! TX: a1b2c3d4e5f6...
```

## ⚠️ Безопасность

- **НЕ коммитьте** мнемоническую фразу в Git
- Используйте только переменные окружения Railway
- Регулярно проверяйте баланс сервисного кошелька
- Мониторьте транзакции в TON Explorer

## 🧪 Тестирование

1. Добавьте `SERVICE_WALLET_MNEMONIC` в Railway
2. Пополните сервисный кошелек на 1-2 TON
3. Создайте тестовый платеж на 50-100 RUB
4. Проверьте логи Railway - должны появиться реальные переводы
5. Проверьте получателя - TON должны прийти на кошелек

## 🚨 Если что-то не работает:

### Ошибка "SERVICE_WALLET_MNEMONIC not configured":
- Проверьте, что переменная добавлена в Railway
- Убедитесь, что нет лишних пробелов
- Должно быть ровно 24 слова

### Ошибка "Insufficient balance":
- Пополните сервисный кошелек
- Учитывайте комиссию ~0.05 TON за транзакцию

### Ошибка "pytoniq library not installed":
- Railway должен автоматически установить из requirements.txt
- Проверьте логи деплоя

---

## 🎉 После настройки:

**Система будет автоматически отправлять реальные TON на подключенные кошельки!**

**Никаких симуляций - только настоящие переводы! 🚀** 