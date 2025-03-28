import streamlit as st
import pandas as pd
import os
from utils import compute_grade_boundaries, validate_boundaries, plot_grade_distribution, clean_data
import streamlit_authenticator as stauth
import plotly.express as px
import hashlib

# Global authenticator instance
authenticator = None

# Load configuration from environment variables
def load_config():
    """Load authentication configuration from environment variables."""
    config = {
        'credentials': {
            'usernames': {
                'user1': {
                    'email': os.getenv('USER1_EMAIL', 'user1@example.com'),
                    'name': os.getenv('USER1_NAME', 'User One'),
                    'password': os.getenv('USER1_PASSWORD', 'abc123')  # Plain text for simplicity; hash in production
                },
                'user2': {
                    'email': os.getenv('USER2_EMAIL', 'user2@example.com'),
                    'name': os.getenv('USER2_NAME', 'User Two'),
                    'password': os.getenv('USER2_PASSWORD', 'xyz789')
                }
            }
        },
        'cookie': {
            'expiry_days': int(os.getenv('COOKIE_EXPIRY_DAYS', 30)),
            'key': os.getenv('COOKIE_KEY', 'random_key'),
            'name': os.getenv('COOKIE_NAME', 'grading_app_cookie')
        },
        'preauthorized': {
            'emails': [os.getenv('PREAUTHORIZED_EMAIL', 'admin@example.com')]
        }
    }
    return config

# Initialize authenticator
def init_authenticator():
    """Set up Streamlit authenticator."""
    global authenticator
    config = load_config()
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    return authenticator

# Signup function (disabled for deployment; manage users via environment variables)
def signup():
    st.subheader("Sign Up")
    st.warning("Signup is disabled in this deployed version. Contact the admin to add new users.")
    if st.button("Back to Login"):
        st.session_state['page'] = 'login'
        st.rerun()

# Main app function
def main_app():
    """Main grading application interface."""
    st.title("📊 AI-Powered Grade Moderation System")
    st.write(f'Welcome, *{st.session_state["name"]}*!')
    st.sidebar.title("User Options")
    authenticator.logout('Logout', 'sidebar')

    st.sidebar.write("### 🎓 Custom Grade Labels")
    st.sidebar.info("Enter grades from highest to lowest (e.g., 'A,B,C,D,F').")
    custom_labels = st.sidebar.text_input("Enter custom grade labels (comma-separated):", "")
    if custom_labels:
        grade_labels = [label.strip() for label in custom_labels.split(',')]
    else:
        grade_labels = ['A+', 'A', 'B', 'C', 'D', 'E', 'F']
    
    if len(grade_labels) < 2:
        st.error("🚨 Please provide at least two grade labels.")
        return
    
    grade_centric = st.selectbox("🎯 Select the grade to be most frequent (centered in the bell curve):", grade_labels)
    
    with st.spinner("Uploading your file..."):
        uploaded_file = st.file_uploader("📂 Upload a CSV or Excel file", type=["csv", "xlsx"])
    
    if uploaded_file:
        with st.spinner('Processing your data...'):
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
            
            if 'marks' not in df.columns:
                st.error("🚨 The uploaded file must contain a 'marks' column.")
                return
            
            df = clean_data(df)
            st.success("Data processed successfully!")
        
        tab1, tab2 = st.tabs(["Grading", "Statistics & Visualizations"])
        
        with tab1:
            df, boundaries = compute_grade_boundaries(df, grade_labels, grade_centric)
            
            st.sidebar.write("### ✏️ Adjust Grade Ranges (Manual Override)")
            manual_boundaries = {}
            for grade in grade_labels[:-1]:
                manual_boundaries[grade] = st.sidebar.slider(f"{grade} minimum marks", 
                                                             0.0, 100.0, 
                                                             float(boundaries[grade]), 
                                                             step=0.1)
            manual_boundaries[grade_labels[-1]] = 0
            
            if not validate_boundaries(grade_labels, manual_boundaries):
                st.sidebar.error("🚨 Grade boundaries must be in descending order. Please adjust the sliders.")
            else:
                df, boundaries = compute_grade_boundaries(df, grade_labels, grade_centric, manual_boundaries)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("### 📌 Computed Grade Ranges")
                    boundary_df = pd.DataFrame(list(boundaries.items()), columns=['Grade', 'Minimum Marks'])
                    st.table(boundary_df)
                
                with col2:
                    st.write("### 📊 Updated Grade Distribution")
                    fig = plot_grade_distribution(df, grade_labels)
                    st.plotly_chart(fig)
                
                st.write("### 📝 Updated Data Preview")
                st.dataframe(df.head(20))
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Updated File", csv, "graded_students.csv", "text/csv")
        
        with tab2:
            st.write("### 📈 Statistics")
            stats = {
                "Mean": df['marks'].mean(),
                "Median": df['marks'].median(),
                "Mode": df['marks'].mode().values[0] if not df['marks'].mode().empty else "N/A",
                "Standard Deviation": df['marks'].std(),
                "Minimum": df['marks'].min(),
                "Maximum": df['marks'].max(),
            }
            stats_df = pd.DataFrame(list(stats.items()), columns=['Statistic', 'Value'])
            st.table(stats_df)
            
            st.write("### 📊 Visualizations")
            plot_type = st.selectbox("Select plot type:", ["Histogram", "Box Plot", "Bar Chart"])
            
            if plot_type == "Histogram":
                fig = px.histogram(df, x='marks', title='Distribution of Marks', nbins=20)
                st.plotly_chart(fig)
            elif plot_type == "Box Plot":
                fig = px.box(df, y='marks', title='Box Plot of Marks')
                st.plotly_chart(fig)
            elif plot_type == "Bar Chart":
                if 'grade' in df.columns:
                    grade_counts = df['grade'].value_counts().reindex(grade_labels, fill_value=0)
                    fig = px.bar(x=grade_counts.index, y=grade_counts.values, 
                                 labels={'x': 'Grades', 'y': 'Frequency'},
                                 title='Grade Distribution')
                    st.plotly_chart(fig)
                else:
                    st.write("Please assign grades in the 'Grading' tab to see the bar chart.")

def main():
    """Main function to manage page navigation."""
    global authenticator
    st.set_page_config(page_title="AI-Powered Grading System", layout="wide")
    
    if authenticator is None:
        authenticator = init_authenticator()
    
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None
    if 'name' not in st.session_state:
        st.session_state['name'] = None
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    
    if st.session_state['authentication_status'] is True:
        main_app()
    else:
        if st.session_state['page'] == 'login':
            st.title("Login")
            login_result = authenticator.login(key='login_form', location='main')
            
            if login_result is not None:
                name, authentication_status, username = login_result
                st.session_state['name'] = name
                st.session_state['authentication_status'] = authentication_status
                st.session_state['username'] = username
                
                if authentication_status:
                    st.session_state['page'] = 'main'
                    st.rerun()
                elif authentication_status is False:
                    st.error('Username/password is incorrect')
                elif authentication_status is None:
                    st.warning('Please enter your username and password')
            
            if st.button("Need an account? Sign Up"):
                st.session_state['page'] = 'signup'
                st.rerun()
        
        elif st.session_state['page'] == 'signup':
            signup()
            if st.button("Back to Login"):
                st.session_state['page'] = 'login'
                st.rerun()

if __name__ == "__main__":
    main()