import streamlit as st
import pandas as pd
from datetime import datetime
import json

# Initialize session state
if 'assessment_submitted' not in st.session_state:
    st.session_state.assessment_submitted = False
if 'assessment_results' not in st.session_state:
    st.session_state.assessment_results = None

# Enhanced Vendor Scorer Logic
class EnhancedVendorScorer:
    def __init__(self, responses):
        self.responses = responses
        self.score = 0
        self.badge = None
        self.category_scores = {}
        self.recommendations = []
        self.risk_factors = []

    def calculate_score(self):
        r = self.responses
        self.category_scores = {}

        # --- Core Identity (40 points max) ---
        identity_score = 0
        identity_score += 5 if r.get("name") else 0
        
        phone_score = {"0": 0, "1": 6, "2": 10}.get(r.get("phones_verified", "0"), 0)
        identity_score += phone_score
        
        address_score = {"none": 0, "partial": 5, "full": 10}.get(r.get("address", "none"), 0)
        identity_score += address_score
        
        social_score = {"none": 0, "personal": 2, "active": 5}.get(r.get("social_media", "none"), 0)
        identity_score += social_score
        
        id_score = {"missing": 0, "unclear": 5, "clear": 10}.get(r.get("id", "missing"), 0)
        identity_score += id_score
        
        self.category_scores["Core Identity"] = identity_score

        # --- Trust & Guarantors (15 points max) ---
        trust_score = {"0": 0, "1": 8, "2": 15}.get(r.get("family_contacts", "0"), 0)
        self.category_scores["Trust & Guarantors"] = trust_score

        # --- Business Legitimacy (30 points max) ---
        business_score = 0
        reg_score = {"none": 0, "smedan": 5, "cac": 10}.get(r.get("registration", "none"), 0)
        business_score += reg_score
        
        supplier_score = {"none": 0, "verbal": 3, "whatsapp": 6, "invoice": 10}.get(r.get("supplier_proof", "none"), 0)
        business_score += supplier_score
        
        ops_score = {"none": 0, "screenshots": 3, "products": 6, "photos": 10}.get(r.get("operations", "none"), 0)
        business_score += ops_score
        
        self.category_scores["Business Legitimacy"] = business_score

        # --- Service Quality (15 points max) ---
        service_score = 0
        refund_score = {"none": 0, "vague": 1, "verbal": 3, "documented": 5}.get(r.get("refund_policy", "none"), 0)
        service_score += refund_score
        
        delivery_score = {"none": 0, "vague": 0, "general": 3, "specific": 5}.get(r.get("delivery_timeline", "none"), 0)
        service_score += delivery_score
        
        refs = int(r.get("references", 0))
        ref_score = 5 if refs >= 3 else (3 if refs in [1,2] else 0)
        service_score += ref_score
        
        self.category_scores["Service Quality"] = service_score

        # --- Bonus/Penalty ---
        bonus_penalty = 0
        resp_score = {"slow": -3, "medium": 2, "fast": 5}.get(r.get("responsiveness", "medium"), 0)
        bonus_penalty += resp_score
        
        comm_score = 3 if r.get("communication") == "professional" else 0
        bonus_penalty += comm_score
        
        red_flags_penalty = -10 * int(r.get("red_flags", 0))
        bonus_penalty += red_flags_penalty
        
        self.category_scores["Bonus/Penalty"] = bonus_penalty

        # Calculate total
        self.score = sum(self.category_scores.values())
        
        # Generate recommendations and risk factors
        self._generate_recommendations()
        self._identify_risk_factors()
        
        return self.score

    def _generate_recommendations(self):
        r = self.responses
        self.recommendations = []
        
        if not r.get("name"):
            self.recommendations.append("❌ Obtain complete business/individual name")
        if r.get("phones_verified", "0") != "2":
            self.recommendations.append("📞 Verify all phone numbers provided")
        if r.get("address", "none") != "full":
            self.recommendations.append("🏠 Request complete address with verification")
        if r.get("id", "missing") != "clear":
            self.recommendations.append("🆔 Obtain clear photo ID documentation")
        if r.get("registration", "none") == "none":
            self.recommendations.append("📋 Request business registration documents")
        if r.get("supplier_proof", "none") in ["none", "verbal"]:
            self.recommendations.append("📄 Request formal supplier documentation")
        if int(r.get("references", 0)) < 3:
            self.recommendations.append("👥 Collect more customer references")
        if r.get("refund_policy", "none") != "documented":
            self.recommendations.append("📝 Document clear refund policy")

    def _identify_risk_factors(self):
        r = self.responses
        self.risk_factors = []
        
        if int(r.get("red_flags", 0)) > 0:
            self.risk_factors.append(f"🚩 {r.get('red_flags')} red flags identified")
        if r.get("responsiveness") == "slow":
            self.risk_factors.append("⏰ Poor communication responsiveness")
        if r.get("communication") != "professional":
            self.risk_factors.append("💬 Unprofessional communication style")
        if r.get("phones_verified", "0") == "0":
            self.risk_factors.append("📱 No phone verification completed")
        if r.get("registration", "none") == "none":
            self.risk_factors.append("🏢 No business registration on file")

    def assign_badge(self):
        if self.score >= 80:
            self.badge = "🟢 Green (Verified)"
            self.status = "APPROVED"
            self.description = "Low risk vendor with strong verification"
        elif self.score >= 60:
            self.badge = "🟡 Yellow (Conditional)"
            self.status = "CONDITIONAL"
            self.description = "Medium risk - proceed with caution and monitoring"
        else:
            self.badge = "🔴 Red (Rejected)"
            self.status = "REJECTED"
            self.description = "High risk - requires significant improvements"
        return self.badge

    def get_score_breakdown(self):
        return pd.DataFrame([
            {"Category": cat, "Score": score, "Max": max_scores[cat]} 
            for cat, score in self.category_scores.items()
        ])

# Maximum possible scores for each category
max_scores = {
    "Core Identity": 40,
    "Trust & Guarantors": 15,
    "Business Legitimacy": 30,
    "Service Quality": 15,
    "Bonus/Penalty": 8
}

# ---------------- Enhanced Streamlit UI ----------------
st.set_page_config(
    page_title="Vendor Verification System", 
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4CAF50;
    }
    .risk-item {
        background-color: #ffebee;
        color: #d32f2f;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        border-left: 3px solid #f44336;
    }
    .recommendation-item {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.25rem;
        border-left: 3px solid #2196F3;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🛡️ Enhanced Vendor Verification System")
st.markdown("### Comprehensive vendor assessment with detailed scoring and recommendations")

# Sidebar for quick info
with st.sidebar:
    st.markdown("## 📊 Scoring Guide")
    st.markdown("**🟢 Green (80-100)**: Verified, low risk")
    st.markdown("**🟡 Yellow (60-79)**: Conditional approval")
    st.markdown("**🔴 Red (0-59)**: High risk, rejected")
    
    st.markdown("## 📋 Categories")
    for cat, max_score in max_scores.items():
        st.markdown(f"**{cat}**: {max_score} pts max")
    
    if st.session_state.assessment_submitted:
        if st.button("🔄 Reset Assessment", use_container_width=True):
            st.session_state.assessment_submitted = False
            st.session_state.assessment_results = None
            st.rerun()

# Main form
col1, col2 = st.columns([2, 1])

with col1:
    with st.form("enhanced_vendor_form"):
        st.markdown("## 👤 Core Identity Verification")
        name = st.checkbox("✅ Full name / business name provided")
        phones_verified = st.radio(
            "📞 Phone numbers verified", 
            ["0", "1", "2"],
            format_func=lambda x: f"{x} number(s) verified"
        )
        address = st.radio(
            "🏠 Address quality", 
            ["none", "partial", "full"],
            format_func=lambda x: x.title()
        )
        social_media = st.radio(
            "📱 Social media presence", 
            ["none", "personal", "active"],
            format_func=lambda x: x.title().replace("_", " ")
        )
        id_quality = st.radio(
            "🆔 Photo ID verification", 
            ["missing", "unclear", "clear"],
            format_func=lambda x: x.title()
        )
        
        st.markdown("## 🤝 Trust & Guarantors")
        family_contacts = st.radio(
            "👨‍👩‍👧‍👦 Family contacts / guarantors", 
            ["0", "1", "2"],
            format_func=lambda x: f"{x} contact(s) provided"
        )
        
        st.markdown("## 🏢 Business Legitimacy")
        registration = st.radio(
            "📋 Business registration", 
            ["none", "smedan", "cac"],
            format_func=lambda x: x.upper() if x != "none" else "None"
        )
        supplier_proof = st.radio(
            "📄 Supplier documentation", 
            ["none", "verbal", "whatsapp", "invoice"],
            format_func=lambda x: x.title()
        )
        operations = st.radio(
            "🏭 Operations evidence", 
            ["none", "screenshots", "products", "photos"],
            format_func=lambda x: x.title()
        )
        
        st.markdown("## ⭐ Service Quality")
        refund_policy = st.radio(
            "💰 Refund policy", 
            ["none", "vague", "verbal", "documented"],
            format_func=lambda x: x.title()
        )
        delivery_timeline = st.radio(
            "🚚 Delivery commitments", 
            ["none", "vague", "general", "specific"],
            format_func=lambda x: x.title()
        )
        references = st.number_input(
            "👥 Customer references/testimonials", 
            min_value=0, max_value=10, value=0
        )
        
        st.markdown("## 📈 Performance Factors")
        responsiveness = st.radio(
            "⚡ Response time", 
            ["slow", "medium", "fast"],
            format_func=lambda x: f"{x.title()} (>24h, 2-24h, <2h)"
        )
        communication = st.radio(
            "💬 Communication quality", 
            ["poor", "professional"],
            format_func=lambda x: x.title()
        )
        red_flags = st.number_input(
            "🚩 Red flags identified", 
            min_value=0, max_value=5, value=0,
            help="Issues like inconsistent info, pressure tactics, etc."
        )

        # Vendor details for record keeping
        st.markdown("## 📝 Vendor Information (Optional)")
        vendor_name = st.text_input("Vendor/Business Name")
        vendor_category = st.selectbox(
            "Business Category",
            ["", "Electronics", "Fashion", "Food & Beverage", "Services", "Manufacturing", "Beauty", "Health & Wellness", "Transportation & Logistics", "Dropshipping", "Gadget", "Other"]
        )
        assessment_date = st.date_input("Assessment Date", datetime.now())

        submitted = st.form_submit_button("🔍 Calculate Verification Score", use_container_width=True)

        # Store results in session state when form is submitted
        if submitted:
            st.session_state.assessment_submitted = True
            # Store all the form data and results
            responses = {
                "name": name,
                "phones_verified": phones_verified,
                "address": address,
                "social_media": social_media,
                "id": id_quality,
                "family_contacts": family_contacts,
                "registration": registration,
                "supplier_proof": supplier_proof,
                "operations": operations,
                "refund_policy": refund_policy,
                "delivery_timeline": delivery_timeline,
                "references": references,
                "responsiveness": responsiveness,
                "communication": communication,
                "red_flags": red_flags,
                "vendor_name": vendor_name,
                "vendor_category": vendor_category,
                "assessment_date": assessment_date
            }
            
            scorer = EnhancedVendorScorer(responses)
            total = scorer.calculate_score()
            badge = scorer.assign_badge()
            
            st.session_state.assessment_results = {
                'responses': responses,
                'scorer': scorer,
                'total': total,
                'badge': badge
            }

with col2:
    if st.session_state.assessment_submitted and st.session_state.assessment_results:
        results = st.session_state.assessment_results
        scorer = results['scorer']
        total = results['total']
        badge = results['badge']
        
        responses = {
            "name": name,
            "phones_verified": phones_verified,
            "address": address,
            "social_media": social_media,
            "id": id_quality,
            "family_contacts": family_contacts,
            "registration": registration,
            "supplier_proof": supplier_proof,
            "operations": operations,
            "refund_policy": refund_policy,
            "delivery_timeline": delivery_timeline,
            "references": references,
            "responsiveness": responsiveness,
            "communication": communication,
            "red_flags": red_flags
        }

        scorer = EnhancedVendorScorer(responses)
        total = scorer.calculate_score()
        badge = scorer.assign_badge()

        # Results display
        st.markdown("## 📊 Assessment Results")
        
        # Score display
        col_score, col_badge = st.columns(2)
        with col_score:
            st.metric("Total Score", f"{total}/100", delta=f"{total-50} from baseline")
        with col_badge:
            st.markdown(f"### {badge}")
        
        st.markdown(f"**Status**: {scorer.status}")
        st.markdown(f"**Assessment**: {scorer.description}")
        
        # Score breakdown chart
        st.markdown("### 📈 Category Breakdown")
        breakdown_df = scorer.get_score_breakdown()
        
        # Create progress bars for each category
        for _, row in breakdown_df.iterrows():
            if row['Max'] > 0:
                progress = max(0.0, min(1.0, row['Score'] / row['Max']))
                color = "red" if row['Score'] < 0 else "normal"
            else:
                progress = 0
            st.progress(progress, text=f"{row['Category']}: {row['Score']}/{row['Max']}")

# Full-width results section
if st.session_state.assessment_submitted and st.session_state.assessment_results:
    results = st.session_state.assessment_results
    scorer = results['scorer']
    total = results['total']
    vendor_name = results['responses']['vendor_name']
    vendor_category = results['responses']['vendor_category']
    assessment_date = results['responses']['assessment_date']
    
    st.markdown("---")
    
    col_rec, col_risk = st.columns(2)
    
    with col_rec:
        st.markdown("### 💡 Recommendations")
        if scorer.recommendations:
            for rec in scorer.recommendations:
                st.markdown(f'<div class="recommendation-item">{rec}</div>', unsafe_allow_html=True)
        else:
            st.success("✅ All verification criteria met!")
    
    with col_risk:
        st.markdown("### ⚠️ Risk Factors")
        if scorer.risk_factors:
            for risk in scorer.risk_factors:
                st.markdown(f'<div class="risk-item">{risk}</div>', unsafe_allow_html=True)
        else:
            st.success("✅ No significant risk factors identified!")
    
    # Export functionality
    st.markdown("### 📋 Assessment Summary")
    
    # Create summary data
    summary_data = {
        "Vendor Name": vendor_name or "Not specified",
        "Category": vendor_category or "Not specified",
        "Assessment Date": str(assessment_date),
        "Total Score": total,
        "Badge": badge,
        "Status": scorer.status,
        "Category Scores": dict(scorer.category_scores),
        "Recommendations": scorer.recommendations,
        "Risk Factors": scorer.risk_factors
    }
    
    # Display as expandable JSON
    with st.expander("📄 Detailed Report (JSON)"):
        st.json(summary_data)
    
    # Multiple download formats
    st.markdown("### 📥 Download Options")
    
    # Company logo upload option
    st.markdown("#### 🏢 Company Branding (Optional)")
    uploaded_logo = st.file_uploader(
        "Upload company logo for certificate (PNG/JPG)", 
        type=['png', 'jpg', 'jpeg'], 
        help="Logo will be displayed in the certificate. Recommended size: 200x100px"
    )
    
    uploaded_signature = st.file_uploader(
    "Upload signature image for certificate (PNG/JPG)", 
    type=['png', 'jpg', 'jpeg'], 
    help="Signature will be displayed in the certificate footer. Recommended size: 300x100px"
    
    )
    col_json, col_pdf, col_csv = st.columns(3)
    
    # JSON download
    json_string = json.dumps(summary_data, indent=2, default=str)
    with col_json:
        st.download_button(
            label="📄 Download JSON",
            data=json_string,
            file_name=f"vendor_assessment_{vendor_name or 'unknown'}_{assessment_date}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # Generate logo data URL if uploaded
    logo_html = ""
    if uploaded_logo is not None:
        import base64
        logo_bytes = uploaded_logo.getvalue()
        logo_b64 = base64.b64encode(logo_bytes).decode()
        logo_html = f'<img src="data:image/{uploaded_logo.type.split("/")[1]};base64,{logo_b64}" alt="Company Logo" class="logo">'
    
    signature_html = ""
    if uploaded_signature is not None:
        import base64
        sig_bytes = uploaded_signature.getvalue()
        sig_b64 = base64.b64encode(sig_bytes).decode()
    signature_html = f'<img src="data:image/{uploaded_signature.type.split("/")[1]};base64,{sig_b64}" alt="Signature" style="max-height: 60px; max-width: 200px; display: block; margin: 10px auto;">'
        
    # Professional Certificate-style HTML
    certificate_color = "#008000" if 'Green' in badge else "#d97706" if 'Yellow' in badge else "#dc2626"
    status_icon = "🟢" if 'Green' in badge else "🟡" if 'Yellow' in badge else "🔴"
    
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vendor Verification Certificate</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                -webkit-print-color-adjust: exact !important;
                color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            
            @page {{
                size: A4;
                margin: 0.5in;
            }}
            
            body {{
                font-family: 'Inter', Arial, sans-serif;
                background: white !important;
                color: #000 !important;
                line-height: 1.4;
                font-size: 12px;
            }}
            
            .certificate-container {{
                max-width: 100%;
                margin: 0;
                background: white !important;
                border: 3px solid {certificate_color} !important;
                border-radius: 8px;
                padding: 20px;
                page-break-inside: avoid;
            }}
            
            .certificate-border {{
                display: none; /* Remove for PDF */
            }}
            
            .header {{
                background: {certificate_color} !important;
                color: white !important;
                padding: 30px 20px;
                text-align: center;
                border-radius: 6px;
                margin-bottom: 20px;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .logo {{
                max-height: 50px;
                max-width: 150px;
                margin-bottom: 15px;
                display: block;
                margin-left: auto;
                margin-right: auto;
                border-radius: 100px
            }}
            
            .certificate-title {{
                font-size: 22px !important;
                font-weight: 700 !important;
                margin-bottom: 8px;
                color: white !important;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .certificate-subtitle {{
                font-size: 14px !important;
                font-weight: 300;
                color: white !important;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .content {{
                padding: 20px 10px;
            }}
            
            .vendor-info {{
                text-align: center;
                margin-bottom: 20px;
                padding: 20px;
                background: #f8f9fa !important;
                border: 2px solid {certificate_color} !important;
                border-radius: 6px;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .vendor-name {{
                font-size: 24px !important;
                font-weight: 700 !important;
                color: #000 !important;
                margin-bottom: 8px;
                text-transform: uppercase;
            }}
            
            .vendor-category {{
                font-size: 14px !important;
                color: #333 !important;
                font-weight: 500;
            }}
            
            .status-badge {{
                display: inline-block;
                font-size: 18px !important;
                font-weight: 700 !important;
                padding: 15px 30px;
                border-radius: 25px;
                margin: 15px 0;
                background: {certificate_color} !important;
                color: white !important;
                text-align: center;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .score-display {{
                font-size: 36px !important;
                font-weight: 700 !important;
                color: {certificate_color} !important;
                text-align: center;
                margin: 15px 0;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .assessment-grid {{
                display: table;
                width: 100%;
                margin: 20px 0;
                page-break-inside: avoid;
            }}
            
            .assessment-section {{
                display: table-cell;
                width: 48%;
                background: #f8f9fa !important;
                padding: 15px;
                border: 1px solid {certificate_color} !important;
                border-radius: 6px;
                margin: 0 1%;
                vertical-align: top;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .assessment-section:first-child {{
                margin-right: 2%;
            }}
            
            .section-title {{
                font-size: 16px !important;
                font-weight: 600 !important;
                color: #000 !important;
                margin-bottom: 10px;
                border-bottom: 2px solid {certificate_color} !important;
                padding-bottom: 5px;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .category-score {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #ddd !important;
                font-weight: 500;
                color: #000 !important;
            }}
            
            .category-score:last-child {{
                border-bottom: none !important;
            }}
            
            .score-value {{
                color: {certificate_color} !important;
                font-weight: 700 !important;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .recommendations-list, .risks-list {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            
            .recommendations-list li, .risks-list li {{
                padding: 6px 0;
                color: #333 !important;
                font-weight: 400;
                line-height: 1.3;
                font-size: 11px;
                border-bottom: 1px dotted #ccc;
            }}
            
            .recommendations-list li:last-child, .risks-list li:last-child {{
                border-bottom: none;
            }}
            
            .certificate-footer {{
                background: #f8f9fa !important;
                padding: 20px;
                text-align: center;
                border-top: 3px solid {certificate_color} !important;
                margin-top: 20px;
                border-radius: 6px;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .signature-line {{
                width: 150px;
                height: 2px;
                background: #333 !important;
                margin: 15px auto 8px;
                -webkit-print-color-adjust: exact !important;
            }}
            
            .signature-text {{
                color: #333 !important;
                font-size: 12px !important;
                font-weight: 600 !important;
            }}
            
            .cert-number {{
                font-family: 'Courier New', monospace;
                color: #666 !important;
                font-size: 10px !important;
                margin-top: 15px;
            }}
            
            .watermark {{
                display: none; /* Remove watermark for cleaner PDF */
            }}
            
            /* Additional PDF-specific fixes */
            table, tr, td, th, tbody, thead, tfoot {{
                page-break-inside: avoid !important;
            }}
            
            h1, h2, h3, h4, h5, h6 {{
                page-break-after: avoid !important;
                page-break-inside: avoid !important;
            }}
            
            img {{
                page-break-inside: avoid !important;
                page-break-after: avoid !important;
            }}
            
            /* Force colors for stubborn browsers */
            div, p, span, h1, h2, h3, h4, h5, h6 {{
                -webkit-print-color-adjust: exact !important;
                color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
            
            /* Flex fallback for older browsers */
            @supports not (display: flex) {{
                .category-score {{
                    display: block;
                }}
                .category-score span:last-child {{
                    float: right;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="certificate-container">
            <div class="certificate-border"></div>
            <div class="watermark">{status_icon}</div>
            
            <div class="header">
                {logo_html}
                <h1 class="certificate-title">VENDOR VERIFICATION CERTIFICATE</h1>
                <p class="certificate-subtitle">Official Assessment & Compliance Verification</p>
            </div>
            
            <div class="content">
                <div class="vendor-info">
                    <div class="vendor-name">{summary_data['Vendor Name']}</div>
                    <div class="vendor-category">{summary_data['Category']} • Assessed on {summary_data['Assessment Date']}</div>
                </div>
                
                <div style="text-align: center;">
                    <div class="score-display">{total}/100</div>
                    <div class="status-badge">
                        {badge.replace('🟢', '').replace('🟡', '').replace('🔴', '').strip()}
                    </div>
                    <p style="color: #64748b; font-style: italic; margin-top: 10px;">{scorer.description}</p>
                </div>
                
                <div class="assessment-grid">
                    <div class="assessment-section">
                        <h3 class="section-title">📊 Category Scores</h3>
                        {''.join([f'<div class="category-score"><span>{cat}</span><span class="score-value">{score}/{max_scores[cat]}</span></div>' for cat, score in scorer.category_scores.items()])}
                    </div>
                    
                    <div class="assessment-section">
                        <h3 class="section-title">
                            {'💡 Recommendations' if scorer.recommendations else '⚠️ Risk Factors' if scorer.risk_factors else '✅ Assessment Status'}
                        </h3>
                        {
                            '<ul class="recommendations-list">' + ''.join([f'<li>{rec}</li>' for rec in scorer.recommendations[:5]]) + '</ul>' if scorer.recommendations
                            else '<ul class="risks-list">' + ''.join([f'<li>{risk}</li>' for risk in scorer.risk_factors[:5]]) + '</ul>' if scorer.risk_factors
                            else '<p style="color: #059669; font-weight: 600;">All verification criteria successfully met. Vendor approved for business operations.</p>'
                        }
                    </div>
                </div>
                
                {'<div class="assessment-section" style="margin-top: 20px;"><h3 class="section-title">⚠️ Risk Factors</h3><ul class="risks-list">' + ''.join([f'<li>{risk}</li>' for risk in scorer.risk_factors[:5]]) + '</ul></div>' if scorer.recommendations and scorer.risk_factors else ''}
            </div>
            
            <div class="certificate-footer">
                {signature_html if signature_html else '<div class="signature-line"></div>'}
                <p class="signature-text">Authorized Verification</p>
                <p style="margin-top: 20px; color: #64748b; font-weight: 500;">
                    Generated by ZOLARUX Vendor Verification System v2.0
                </p>
                <p style="color: #94a3b8; font-size: 14px; margin-top: 10px;">
                    Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                </p>
                <p class="cert-number">Certificate ID: VVS-{hash(str(summary_data)) % 100000:05d}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    st.info("""
    📄 **For best PDF results:**
    1. Open the downloaded HTML file in Chrome/Edge
    2. Press Ctrl+P (Cmd+P on Mac)
    3. Enable 'Background graphics' in print settings
    4. Set margins to 'Minimum'
    5. Save as PDF
    """)
    
    with col_pdf:
        st.download_button(
            label="🏆 Download Certificate",
            data=html_report,
            file_name=f"vendor_certificate_{vendor_name or 'unknown'}_{assessment_date}.html",
            mime="text/html",
            use_container_width=True
        )
    
    # CSV download
    csv_data = []
    csv_data.append(['Vendor Assessment Report', ''])
    csv_data.append(['Vendor Name', summary_data['Vendor Name']])
    csv_data.append(['Category', summary_data['Category']])
    csv_data.append(['Assessment Date', summary_data['Assessment Date']])
    csv_data.append(['Total Score', f"{total}/100"])
    csv_data.append(['Badge', badge])
    csv_data.append(['Status', scorer.status])
    csv_data.append(['', ''])
    csv_data.append(['Category Scores', ''])
    for cat, score in scorer.category_scores.items():
        csv_data.append([cat, f"{score}/{max_scores[cat]}"])
    csv_data.append(['', ''])
    csv_data.append(['Recommendations', ''])
    for i, rec in enumerate(scorer.recommendations, 1):
        csv_data.append([f"Recommendation {i}", rec])
    csv_data.append(['', ''])
    csv_data.append(['Risk Factors', ''])
    for i, risk in enumerate(scorer.risk_factors, 1):
        csv_data.append([f"Risk {i}", risk])
    
    csv_string = '\n'.join([','.join([f'"{cell}"' for cell in row]) for row in csv_data])
    
    with col_csv:
        st.download_button(
            label="📊 Download CSV",
            data=csv_string,
            file_name=f"vendor_assessment_{vendor_name or 'unknown'}_{assessment_date}.csv",
            mime="text/csv",
            use_container_width=True
        )

# Footer
st.markdown("---")
st.markdown("*ZOLARUX Vendor Verification System v2.0 - Enhanced with detailed analytics and recommendations*")