#!/usr/bin/env python3
"""
Movie Magic - Smart Movie Ticket Booking System (DynamoDB only)
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import boto3
import uuid
import os

app = Flask(__name__)
app.secret_key = 'fallback_dev_key'

# ------------------- AWS DynamoDB + SNS Setup ------------------- #
AWS_REGION = 'us-east-1'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:376129862283:MovieTicketBookingTopic:eb559647-c808-4bc1-abf4-2c979e9be2e6'

dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns = boto3.client('sns', region_name=AWS_REGION)

users_table = dynamodb.Table('MovieMagicUsers')
movies_table = dynamodb.Table('MovieMagicMovies')
bookings_table = dynamodb.Table('MovieMagicBookings')

# ------------------- Helper Functions ------------------- #
def send_notification(booking, subject, message):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message,
            MessageAttributes={
                'email': {'DataType': 'String', 'StringValue': booking['booked_by']}
            }
        )
        print("✅ Notification sent via SNS")
    except Exception as e:
        print("❌ SNS Error:", e)

def get_movie_by_id(movie_id):
    try:
        response = movies_table.get_item(Key={'id': movie_id})
        return response.get('Item')
    except Exception as e:
        print("❌ Error fetching movie:", e)
        return None

# ------------------- Routes ------------------- #
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])

        try:
            users_table.put_item(Item={
                'email': email,
                'name': name,
                'phone': phone,
                'password': password
            })
            flash("Signup successful. Please log in.")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Signup error: {e}", 'error')
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            response = users_table.get_item(Key={'email': email})
            user = response.get('Item')
            if user and check_password_hash(user['password'], password):
                session['user'] = {'email': user['email'], 'name': user['name']}
                return redirect(url_for('index'))
            else:
                return "Invalid credentials"
        except Exception as e:
            return f"Login error: {e}"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/movies')
def movies():
    try:
        response = movies_table.scan()
        return render_template('movies.html', movies=response['Items'])
    except Exception as e:
        return f"Error loading movies: {e}"

@app.route("/movie_details")
def movie_details():
    movie_id = request.args.get("id")
    movie = get_movie_by_id(movie_id)
    if movie:
        return render_template("movie_details.html", movie=movie)
    return "Movie not found", 404

@app.route('/seat_selection')
def seat_selection():
    movie_id = request.args.get('movie')
    theatre = request.args.get('theatre')
    showtime = request.args.get('showtime')
    movie = get_movie_by_id(movie_id)
    return render_template('seat_selection.html', movie=movie, theatre=theatre, showtime=showtime)

@app.route('/payment')
def payment():
    return render_template('payment.html')

@app.route('/dashboard')
def dashboard():
    user = session.get('user')
    return render_template('dashboard.html', user=user)


@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    try:
        data = request.json
        user = session.get('user', {'email': 'guest@example.com', 'name': 'Guest'})
        booking_id = str(uuid.uuid4())
        booking = {
            'id': booking_id,
            'movie': data['movie'],
            'date': data['date'],
            'time': data['time'],
            'theatre': data['theatre'],
            'seats': data['seats'],
            'tickets': data['tickets'],
            'price': data['price'],
            'booked_by': user['email'],
            'timestamp': datetime.utcnow().isoformat()
        }

        bookings_table.put_item(Item=booking)

        subject = f"🎟 Booking Confirmed: {data['movie']}"
        message = f"Hi {user.get('name')}, your booking for '{data['movie']}' at {data['time']} on {data['date']} is confirmed.\nSeats: {', '.join(data['seats'])}\nTickets: {data['tickets']}\nPrice: {data['price']}"
        send_notification(booking, subject, message)

        return jsonify({'status': 'success', 'booking_id': booking_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/seed_movies')
def seed_movies():
    try:
        movies = [
        {
            "id": "1",
            "title": "Kingdom",
            "language": "Telugu",
            "genre": "Action, Drama",
            "price": "Rs180",
            "image": "https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcRfHoiBliijeRVAi4GY_TryAITeBeTRxlayps0eJUaPY74b732T",
            "description": "The film revolves around a terrorist attack on an American housing compound in Riyadh, Saudi Arabia. FBI Special Agent Ronald Fleury leads a team to investigate the attack, facing resistance from Saudi officials and navigating a complex political landscape. ",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["12:00 PM", "3:00 PM", "6:00 PM"]
                }
            ]
        },
        {
            "id": "2",
            "title": "coolie",
            "language": "telugu",
            "genre": "Action, Adventure, Sci-Fi",
            "price": "Rs200",
            "image": "https://www.wallsnapy.com/img_gallery/coolie-movie-rajini--poster-4k-download-9445507.jpg",
            "description": "The plot is said to involve a vendetta, driven by the protagonist's desire to right past wrongs from his youth. The film is also reported to have an emotional core, with Deva's quest for revenge shaping his life and purpose. ",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["12:00 PM", "3:00 PM", "6:00 PM"]
                },
                {
                    "name": "IMAX, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                }
            ]
        },
        {
            "id":"3",
            "title": "rajasaab",
            "language": "telugu",
            "genre": "Horror,fatasy",
            "price": "Rs250",
            "image": "https://assets-in.bmscdn.com/discovery-catalog/events/et00383697-gucgrdkcjr-landscape.jpg",
            "description": "A young heir embraces both his royal heritage and rebellious spirit as he rises to power, establishing unprecedented rules during his reign as Raja Saab.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["10:00 AM", "1:30 PM", "6:00 PM"]
                },
                {
                    "name": "IMAX, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                },
            ]
        },
        
        {
            "id": "4",
            "title": "War 2",
            "language": "hindi",
            "genre": "Action, Thriller",
            "price": "Rs200",
            "image": "https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcRcUHzhXmYstYQAUNnsxv-utGFQ0_hpBZJgCgD30p0jqtERSH1y",
            "description": "A rogue mission forces elite agents from rival nations to unite against a deadly global threat. As hidden loyalties unravel, every move could spark international war. Packed with high-octane action and mind games, War 2 raises the stakes like never before.",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["10:00 AM", "1:00 PM", "4:00 PM"]
                }
            ]
        },
        { 
            "id": "5",
            "title": "Devara part-1", 
            "language": "telugu",
            "genre": "Action, Thriller,Drama",
            "price": "Rs200",
            "image": "https://static.toiimg.com/thumb/resizemode-4,width-1280,height-720,msid-113587323/113587323.jpg",
            "description": "The film centers around a conflict between Devara and Bhaira, fueled by Devara's decision to stop smuggling operations, which disrupts the established order. ",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["10:00 AM", "3:30 PM", "8:30 PM"]
                }
            ]
        },
        {
            "id": "6",
            "title": "Nikita Roy",
            "language": "hindi",
            "genre": "Horror, Mystery, Thriller",
            "price": "Rs250",
            "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRYs_PKQZnJRaDUREOPF0fCcFf-gkwQNTNE0QsthsbNjFSE_MIm",
            "description": "Nikita Roy, a fearless investigator, uncovers a dark conspiracy linked to a series of mysterious disappearances. As she delves deeper, the line between truth and illusion begins to blur. A gripping psychological thriller where justice comes at a chilling cost.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["2:00 PM", "5:00 PM", "8:00 PM"]
                },
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["12:00 PM", "3:00 PM", "6:00 PM"]
                }
            ]
        },
        {
            "id": "7",
            "title": "3 BHK",
            "language": "tamil",
            "genre": "Drama, Family",
            "price": "Rs200",
            "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ9zdJ5ZhXj8pRpDBx4ywHu8tCLs6LQmAPRllzYEfgUfgDXUvUu",
            "description": "A middle-class family's dream home turns into a maze of secrets as strange events unfold behind each door. Hidden tensions and mysterious neighbors begin to unravel their peaceful life. 3 BHK is a suspense-filled domestic drama where every room holds a twist.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                }
            ]    
        }, 
 {
            "id": "8",
            "title": "Hari Hara Veera Mallu",
            "language": "telugu",
            "genre": "Action, Drama",
            "price": "Rs250",
            "image": "https://encrypted-tbn2.gstatic.com/images?q=tbn:ANd9GcR2t2qnSxIi9X8qIcUJ8X3ZbNak1nOr5SlyQ-_u-tjMrYgeUk-l",
            "description": "Set in the Mughal era, Veera Mallu, a legendary outlaw, rises against tyranny to steal the prized Koh-i-Noor diamond. Battling empires and destiny, he becomes a symbol of rebellion and justice. Hari Hara Veera Mallu is a grand historical epic blending action, devotion, and heroism.",
            "theatres": [
                {
                    "name": "PVR Cinemas, Kavali",
                    "showtimes": ["11:00 AM", "2:30 PM", "6:30 PM"]
                },
                {
                    "name": "IMAX, Kavali",
                    "showtimes": ["10:00 AM", "1:00 PM", "4:00 PM"]
                }
            ]
        },
        {   
            "id": "9",
            "title": "Kannappa",
            "language": "telugu",
            "genre":  "Action, Epic",
            "price": "Rs300",
            "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQQZFvUvhzgYPzw8sTQReM0ruAAEIEjHkGhMHnO3ytAZGWxsk-p",
            "description": "Based on the legendary devotee of Lord Shiva, Kannapa follows a tribal hunter whose unwavering faith leads to divine transformation. As he challenges societal norms and spiritual tests, his devotion transcends boundaries. A powerful mythological epic celebrating sacrifice, belief, and eternal love for the divine.",
            "theatres": [
                {
                    "name": "Sri Lakshmi Theatre, Kavali",
                    "showtimes": ["10:00 AM", "1:00 PM", "4:00 PM"]
                }
            ]
        }   
    ]
        with movies_table.batch_writer() as batch:
            for movie in movies:
                batch.put_item(Item=movie)

        return "✅ Movies seeded successfully"
    except Exception as e:
        return f"❌ Error seeding movies: {e}"

@app.context_processor
def inject_user():
    return dict(logged_in_user=session.get('user'))

# ------------------- Run Server ------------------- #
if __name__ == '__main__':
    print("🎬 Starting Movie Magic (DynamoDB only)...")
    app.run(debug=True, host='0.0.0.0', port=5000)
