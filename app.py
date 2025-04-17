from flask import Flask, render_template, request, flash, redirect, url_for
import random
import json
from datetime import datetime
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
import os
import logging

# Configuration pour Flask-Mail
app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'centredememorisationdesulis@gmail.com'
app.config['MAIL_PASSWORD'] = 'czys ncaw fuew mrou'
app.config['MAIL_DEFAULT_SENDER'] = 'centredememorisationdesulis@gmail.com'
app.config['MAIL_DEBUG'] = True
app.config['SECRET_KEY'] = 'hadiths-nawawi-reminder-key-2024'

mail = Mail(app)

# Configuration du logging plus détaillé
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger les hadiths depuis le fichier JSON
def load_hadiths():
    try:
        with open('hadiths.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Charger les abonnés
def load_subscribers():
    try:
        with open('subscribers.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Sauvegarder les abonnés
def save_subscribers(subscribers):
    with open('subscribers.json', 'w', encoding='utf-8') as f:
        json.dump(subscribers, f, ensure_ascii=False, indent=4)

def get_daily_hadiths():
    today = datetime.now().strftime('%Y-%m-%d')
    random.seed(today)
    hadiths = load_hadiths()
    daily_hadiths = random.sample(hadiths, 3)
    daily_hadiths.sort(key=lambda x: x['number'])
    return daily_hadiths

def send_daily_hadiths(force=False):
    with app.app_context():  
        try:
            logger.info("=== TÂCHE PLANIFIÉE TRIGGERED ===")
            logger.info(f"Force mode: {force}")
            today = datetime.now().date()

            # Charger les abonnés
            subscribers = load_subscribers()
            logger.info(f"Nombre d'abonnés chargés : {len(subscribers)}")
            logger.info(f"Liste des abonnés : {subscribers}")

            # Charger les hadiths
            with open('hadiths.json', 'r', encoding='utf-8') as f:
                all_hadiths = json.load(f)
                logger.info(f"Nombre total de hadiths chargés : {len(all_hadiths)}")

            success_count = 0
            error_count = 0
            
            # Pour chaque abonné
            for subscriber in subscribers:
                try:
                    email = subscriber['email']
                    hadith_count = subscriber.get('hadith_count', 1)
                    logger.info(f"Préparation de l'envoi pour {email} ({hadith_count} hadith(s))")

                    # Sélectionner des hadiths aléatoires
                    selected_hadiths = random.sample(all_hadiths, min(hadith_count, len(all_hadiths)))
                    logger.info(f"Hadiths sélectionnés : {[h.get('source', 'N/A') for h in selected_hadiths]}")

                    # Créer le contenu HTML
                    html_content = render_template(
                        'email_template.html',
                        hadiths=selected_hadiths,
                        date=today.strftime('%d/%m/%Y')
                    )

                    # Créer le message
                    msg = Message(
                        subject=f'Vos {hadith_count} hadith(s) du jour - {today.strftime("%d/%m/%Y")}',
                        sender='centredememorisationdesulis@gmail.com',
                        recipients=[email]
                    )
                    msg.html = html_content

                    logger.info(f"Configuration du message pour {email}:")
                    logger.info(f"From: {msg.sender}")
                    logger.info(f"To: {msg.recipients}")
                    logger.info(f"Subject: {msg.subject}")

                    # Tentative d'envoi
                    logger.info(f"Tentative d'envoi d'email à {email}...")
                    mail.send(msg)
                    logger.info(f"Email envoyé avec succès à {email}")
                    success_count += 1

                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi à {email}: {str(e)}")
                    error_count += 1
                    continue

            result = f"Envoi terminé. {success_count} email(s) envoyé(s) avec succès, {error_count} erreur(s)."
            logger.info(result)
            return result

        except Exception as e:
            error_msg = f"ERREUR GÉNÉRALE : {str(e)}"
            logger.error(error_msg)
            return error_msg

# Configuration du planificateur
scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_hadiths, 'cron', hour=7, minute=42, misfire_grace_time=None)  # Envoi quotidien à 7h42
scheduler.start()

@app.route('/')
def index():
    daily_hadiths = get_daily_hadiths()
    return render_template('index.html', hadiths=daily_hadiths, datetime=datetime)

@app.route('/all-hadiths')
def all_hadiths():
    with open('hadiths.json', 'r', encoding='utf-8') as f:
        hadiths = json.load(f)
    return render_template('all_hadiths.html', hadiths=hadiths)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    hadith_count = int(request.form.get('hadith_count'))
    
    if not email:
        flash('Veuillez fournir une adresse email valide.', 'error')
        return redirect(url_for('index'))
    
    # Charger les abonnés existants
    subscribers = []
    if os.path.exists('subscribers.json'):
        with open('subscribers.json', 'r') as f:
            old_subscribers = json.load(f)
            # Convertir l'ancien format (liste d'emails) vers le nouveau format (liste d'objets)
            for old_sub in old_subscribers:
                if isinstance(old_sub, str):
                    subscribers.append({
                        'email': old_sub,
                        'hadith_count': 1  # valeur par défaut pour les anciens abonnés
                    })
                else:
                    subscribers.append(old_sub)
    
    # Vérifier si l'email existe déjà
    for subscriber in subscribers:
        if subscriber['email'] == email:
            subscriber['hadith_count'] = hadith_count
            flash('Votre préférence de nombre de hadiths a été mise à jour.', 'success')
            break
    else:
        # Ajouter le nouvel abonné
        subscribers.append({
            'email': email,
            'hadith_count': hadith_count
        })
        flash('Vous êtes maintenant inscrit aux rappels quotidiens !', 'success')
    
    # Sauvegarder les modifications
    with open('subscribers.json', 'w') as f:
        json.dump(subscribers, f, indent=4)
    
    return redirect(url_for('index'))

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    email = request.form.get('email')
    if not email:
        flash('Veuillez entrer une adresse email valide.', 'error')
        return redirect(url_for('index'))
    
    subscribers = load_subscribers()
    if email in subscribers:
        subscribers.remove(email)
        save_subscribers(subscribers)
        flash('Vous êtes maintenant désinscrit des rappels quotidiens.', 'success')
    else:
        flash('Cette adresse email n\'est pas inscrite.', 'error')
    
    return redirect(url_for('index'))

@app.route('/test-email')
def test_email():
    try:
        logger.info("Début de l'envoi du mail de test...")
        msg = Message(
            'Test - Message Simple',
            sender='centredememorisationdesulis@gmail.com',
            recipients=['lalaouilounes2@gmail.com']
        )
        
        # Message simple pour le test
        msg.body = "Ceci est un message de test simple. Si vous recevez ce message, le système d'envoi d'email fonctionne correctement."
        
        logger.info("Tentative d'envoi du mail...")
        mail.send(msg)
        logger.info("Email envoyé avec succès!")
        return 'Email de test envoyé avec succès!'
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi : {str(e)}")
        return f'Erreur lors de l\'envoi de l\'email : {str(e)}'

@app.route('/test-reminder')
def test_reminder():
    try:
        logger.info("Début du test d'envoi de rappel...")
        
        # Charger les hadiths
        with open('hadiths.json', 'r', encoding='utf-8') as f:
            all_hadiths = json.load(f)
            logger.info(f"Nombre total de hadiths chargés : {len(all_hadiths)}")

        # Sélectionner un hadith aléatoire
        selected_hadith = random.choice(all_hadiths)
        today = datetime.now().date()

        # Créer le contenu de l'email
        html_content = render_template(
            'email_template.html',
            hadiths=[selected_hadith],
            date=today.strftime('%d/%m/%Y')
        )

        # Envoyer l'email
        msg = Message(
            'Test - Rappel Hadith',
            sender='centredememorisationdesulis@gmail.com',
            recipients=['lalaouilounes2@gmail.com'],
            html=html_content
        )
        
        logger.info("Tentative d'envoi du mail de rappel...")
        mail.send(msg)
        logger.info("Email de rappel envoyé avec succès!")
        return 'Email de test de rappel envoyé avec succès!'
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du rappel : {str(e)}")
        return f'Erreur lors de l\'envoi de l\'email de rappel : {str(e)}'

@app.route('/force-send')
def force_send():
    try:
        logger.info("=== DÉBUT DU TEST D'ENVOI FORCÉ ===")
        
        # Vérification de la configuration
        logger.info(f"Configuration email :")
        logger.info(f"MAIL_SERVER: {app.config['MAIL_SERVER']}")
        logger.info(f"MAIL_PORT: {app.config['MAIL_PORT']}")
        logger.info(f"MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}")
        logger.info(f"MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
        
        # Création du message
        msg = Message(
            subject='Test Urgent - Hadiths',
            sender='centredememorisationdesulis@gmail.com',
            recipients=['lalaouilounes2@gmail.com']
        )
        msg.body = f"""
        Test d'envoi urgent
        Heure d'envoi : {datetime.now().strftime('%H:%M:%S')}
        
        Si vous recevez ce message, le système fonctionne.
        """
        
        # Tentative d'envoi
        logger.info("Tentative d'envoi...")
        mail.send(msg)
        logger.info("Email envoyé avec succès!")
        return "Email de test envoyé avec succès!"
        
    except Exception as e:
        error = f"ERREUR : {str(e)}"
        logger.error(error)
        return error

@app.route('/test-all')
def test_all():
    try:
        logger.info("=== DÉBUT DU TEST D'ENVOI À TOUS LES ABONNÉS ===")
        
        # Charger les abonnés
        subscribers = load_subscribers()
        logger.info(f"Nombre d'abonnés : {len(subscribers)}")
        
        # Charger les hadiths
        with open('hadiths.json', 'r', encoding='utf-8') as f:
            all_hadiths = json.load(f)
            logger.info(f"Nombre total de hadiths chargés : {len(all_hadiths)}")

        # Sélectionner un hadith aléatoire pour le test
        selected_hadith = random.choice(all_hadiths)
        today = datetime.now()

        # Créer le contenu de l'email
        html_content = render_template(
            'email_template.html',
            hadiths=[selected_hadith],
            date=today.strftime('%d/%m/%Y')
        )

        success_count = 0
        error_count = 0
        
        # Pour chaque abonné
        for subscriber in subscribers:
            try:
                email = subscriber['email']  # Maintenant on sait que c'est un dictionnaire
                
                # Envoyer l'email
                msg = Message(
                    'Test - Rappel Hadith pour tous les abonnés',
                    sender='centredememorisationdesulis@gmail.com',
                    recipients=[email]
                )
                msg.html = html_content
                
                logger.info(f"Tentative d'envoi à {email}...")
                mail.send(msg)
                logger.info(f"Email envoyé avec succès à {email}")
                success_count += 1
                
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi à {email}: {str(e)}")
                error_count += 1
                continue

        result_message = f"Test terminé. {success_count} email(s) envoyé(s) avec succès, {error_count} erreur(s)."
        logger.info(result_message)
        return result_message
        
    except Exception as e:
        error_message = f"Erreur générale lors du test : {str(e)}"
        logger.error(error_message)
        return error_message

@app.route('/force_send_all')
def force_send_all():
    logger.info("Envoi forcé des hadiths à tous les abonnés...")
    try:
        subscribers = load_subscribers()
        if not subscribers:
            logger.warning("Aucun abonné trouvé!")
            return "Aucun abonné trouvé!"
            
        hadiths = get_daily_hadiths()
        for subscriber in subscribers:
            logger.info(f"Envoi à {subscriber}...")
            msg = Message(
                'Test - Vos 3 Hadiths du jour',
                sender='centredememorisationdesulis@gmail.com',
                recipients=[subscriber]
            )
            msg.html = render_template(
                'email_template.html',
                hadiths=hadiths,
                date=datetime.now().strftime('%d/%m/%Y')
            )
            mail.send(msg)
            logger.info(f"Email envoyé avec succès à {subscriber}")
            
        return "Emails envoyés avec succès à tous les abonnés!"
    except Exception as e:
        error_msg = f"Erreur lors de l'envoi : {str(e)}"
        logger.error(error_msg)
        return error_msg

@app.route('/test-simple')
def test_simple():
    try:
        logger.info("=== DÉBUT DU TEST SIMPLE ===")
        msg = Message(
            subject='Test Simple - Rappel Hadiths',
            sender='centredememorisationdesulis@gmail.com',
            recipients=['lalaouilounes2@gmail.com']
        )
        msg.body = "Ceci est un test simple d'envoi de mail. Si vous recevez ce message, le système fonctionne."
        
        logger.info("Configuration du message :")
        logger.info(f"From: {msg.sender}")
        logger.info(f"To: {msg.recipients}")
        logger.info(f"Subject: {msg.subject}")
        
        mail.send(msg)
        logger.info("Email envoyé avec succès!")
        return "Email de test envoyé avec succès!"
    except Exception as e:
        error = f"Erreur lors de l'envoi : {str(e)}"
        logger.error(error)
        return error
import os
app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
