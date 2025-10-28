# Material Planning Assistant 📦

A comprehensive Streamlit dashboard for material planning and production readiness analysis.

## Features

- **Dashboard Overview**: Real-time metrics and supply distribution analysis
- **Project Deep Dive**: Detailed project status and material requirements
- **Material Inquiry**: Search and analyze specific materials
- **Supplier Performance**: Track supplier delays and performance metrics
- **Production Readiness**: Identify projects ready for production
- **Push to Production**: Action-oriented view with blocking items analysis

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Place your Material Study Excel file in the same directory as the script
   - File should be named: `MV_Material_Study-*.xlsx`

## Usage

Run the app locally:
```bash
streamlit run material_planning_assistant.py
```

## Deployment to Streamlit Cloud

1. Push this repository to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repository
4. Deploy!

## Data Requirements

The app expects an Excel file with a "Study" sheet containing the following columns:
- SEC order
- SEC Number
- product
- item
- description
- req_qty
- allocated_qty
- balance
- supply_type
- source
- locater
- supplier
- delay
- availability_date
- ROH delivery
- SEC delivery
- Asn Expected Date
- Asn Creation Date

## File Structure

```
material-planning-app/
├── material_planning_assistant.py
├── requirements.txt
├── MV_Material_Study-*.xlsx
└── README.md
```

## Author

Material Planning Dashboard v1.0

## License

MIT License
