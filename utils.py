import numpy as np
import pandas as pd
import plotly.express as px

def compute_grade_boundaries(df, grade_labels, grade_centric, manual_boundaries=None):
    """Compute grade boundaries based on a centric grade or manual overrides."""
    total_students = len(df)
    center_idx = grade_labels.index(grade_centric)
    
    if manual_boundaries:
        grade_boundaries = manual_boundaries
    else:
        distribution = np.array([abs(i - center_idx) for i in range(len(grade_labels))])
        distribution = np.max(distribution) - distribution + 1
        distribution = distribution / distribution.sum()
        
        grade_counts = (distribution * total_students).astype(int)
        grade_counts[-1] += total_students - grade_counts.sum()
        
        df_sorted = df.sort_values(by='marks', ascending=False).reset_index(drop=True)
        grade_boundaries = {}
        start_idx = 0
        
        for i, grade in enumerate(grade_labels[:-1]):
            end_idx = start_idx + grade_counts[i]
            if end_idx > total_students:
                end_idx = total_students
            if start_idx < total_students:
                grade_boundaries[grade] = df_sorted.iloc[end_idx - 1]['marks']
            start_idx = end_idx
        
        grade_boundaries[grade_labels[-1]] = 0
    
    df['grade'] = df['marks'].apply(lambda x: next((g for g, b in grade_boundaries.items() if x >= b), grade_labels[-1]))
    return df, grade_boundaries

def validate_boundaries(grade_labels, boundaries):
    """Ensure grade boundaries are in descending order."""
    boundary_values = [boundaries[grade] for grade in grade_labels[:-1]]
    return all(boundary_values[i] > boundary_values[i+1] for i in range(len(boundary_values) - 1))

def plot_grade_distribution(df, grade_labels):
    """Plot the distribution of grades using Plotly."""
    grade_counts = df['grade'].value_counts().reindex(grade_labels, fill_value=0)
    fig = px.bar(x=grade_counts.index, y=grade_counts.values, 
                 labels={'x': 'Grades', 'y': 'Frequency'},
                 title='Grade Distribution', 
                 color=grade_counts.index, 
                 text=grade_counts.values)
    return fig

def clean_data(df):
    """Clean the dataframe by converting marks to numeric and removing invalid rows."""
    df['marks'] = pd.to_numeric(df['marks'], errors='coerce')
    invalid_rows = df[df['marks'].isna()]
    if not invalid_rows.empty:
        print(f"Found {len(invalid_rows)} rows with invalid marks. These will be removed.")
        df = df.dropna(subset=['marks'])
    return df