1. Запустить терминал pycharm
2. Установить зависимости, выполнив в терминале команду: 
   - pip install -r requirements.txt
3. Создать базу данных и пользователя в postgres:
   - выполнить в терминале команды: 
     - перейти в учетную запись postgres:
       - sudo su postgres
     - перейти в оболочку postgres:
       - psql
     - в терминале оболочки postgres выполнить команды:
       - CREATE USER ivanovav WITH PASSWORD 'ivanovav';
       - DROP DATABASE IF EXIST ivanovav;
       - GRANT ALL PRIVILEGES ON DATABASE "ivanovav" to ivanovav; 
       - \c ivanovav
       - GRANT pg_read_all_data TO ivanovav;
       - GRANT pg_write_all_data TO ivanovav;
       - ALTER DATABASE ivanovav OWNER TO ivanovav;
     - выйти из терминала postgres выполнив команду:
       - exit
     - в терминале pycharm выйти из учетной записи postgres:
       - exit
4. Отредактировать .env с учетом настроек рабочего места
5. Выполнить действия, связанные с форматированием созданной 
базы данных, ее разметкой в соответствии с используемыми моделями, 
созданием администратора (суперпользователя):
   - python manage.py makemigrations
   - python manage.py migrate
   - python manage.py createsuperuser
6. Выполнить запуск сервера:
   - python manage.py runserver
7. Открыть второе окно с терминалом pycharm и выполнить запуск 
асинхронного обработчика задач celery:
   - python -m celery -A diplom worker -l info
8. Открыть файл с запросами api_requests.http с помощью редактора vscode и 
выполнить желаемые запросы, используя уже созданные или создавая собственные
9. Выполнить подготовку к тестированию и запустить тестирование:
   - дополнительно создать третье окно с терминалом pycharm
   - выполнить в нем команды: 
     - перейти в учетную запись postgres:
       - sudo su postgres
     - перейти в оболочку postgres:
       - psql
     - в терминале оболочки postgres выполнить команды:
       - DROP DATABASE IF EXIST test_ivanovav;
       - CREATE DATABASE test_ivanovav;
     - выйти из терминала postgres:
       - exit
     - выйти из учетной записи postgres:
       - exit
     - запустить тестирование:
       - pytest test/retail/test.py
10. Перейти по адресу http://127.0.0.1:8000/admin/ с использованием любого браузера
и ввести логин (email) и пароль суперпользователя(админа), указанные при регистрации 
