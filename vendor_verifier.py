import streamlit as st
import pandas as pd
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="Vendor Verification System v3.0",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .score-display {
        font-size: 3rem;
        font-weight: bold;
    }
    .section-header {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .quality-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.25rem;
    }
    .badge-excellent { background-color: #d4edda; color: #155724; }
    .badge-acceptable { background-color: #fff3cd; color: #856404; }
    .badge-poor { background-color: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'vendor_data' not in st.session_state:
    st.session_state.vendor_data = {}
if 'final_score' not in st.session_state:
    st.session_state.final_score = None

# Scoring class
class VendorScorerV3:
    def __init__(self, data):
        self.data = data
        self.score = 0
        self.category_scores = {}
        self.recommendations = []
        self.risk_factors = []
    
    def calculate_auto_score(self):
        """Step 1: Auto-score from form submissions (40 points max)"""
        score = 0
        
        # Basic Information (15 points)
        if self.data.get('has_name'): score += 3
        if self.data.get('has_phone'): score += 4
        if self.data.get('has_address'): score += 4
        if self.data.get('has_social_media'): score += 4
        
        self.category_scores['Basic Information'] = score
        
        # Documents Submitted (25 points)
        doc_score = 0
        if self.data.get('has_id_photo'): doc_score += 5
        doc_score += self.data.get('guarantor_count', 0) * 2.5  # 0, 1, or 2 guarantors
        
        reg_points = {'none': 0, 'smedan': 3, 'cac': 5}
        doc_score += reg_points.get(self.data.get('registration_type', 'none'), 0)
        
        if self.data.get('has_supplier_proof'): doc_score += 5
        if self.data.get('has_operations_proof'): doc_score += 5
        if self.data.get('has_testimonials'): doc_score += 2.5
        
        self.category_scores['Documents Submitted'] = doc_score
        score += doc_score
        
        return score
    
    def calculate_quality_score(self):
        """Step 2: Document quality assessment (35 points max)"""
        quality_points = {'poor': 1, 'acceptable': 3, 'excellent': 5}
        
        score = 0
        score += quality_points.get(self.data.get('id_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('registration_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('supplier_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('operations_quality', 'poor'), 0)
        
        # Testimonial quality (NEW - 10 points)
        testimonial_points = {'suspicious': 0, 'mixed': 5, 'authentic': 10}
        score += testimonial_points.get(self.data.get('testimonial_quality', 'suspicious'), 0)
        
        # Business policies (5 points)
        if self.data.get('has_refund_policy'): score += 2.5
        if self.data.get('has_delivery_info'): score += 2.5
        
        self.category_scores['Document Quality'] = score
        return score
    
    def calculate_interaction_score(self):
        """Step 3: WhatsApp interaction assessment (25 points max)"""
        score = 0
        
        # Responsiveness (1-5 scale = 10 points)
        score += self.data.get('responsiveness_rating', 1) * 2
        
        # Communication quality (10 points)
        comm_points = {'unprofessional': 0, 'professional': 10}
        score += comm_points.get(self.data.get('communication_quality', 'unprofessional'), 0)
        
        # Red flags penalty (up to -15 points, but capped at bringing this section to 0)
        red_flags = self.data.get('red_flags_count', 0)
        penalty = min(red_flags * 5, score)  # Can't go below 0 for this category
        score -= penalty
        
        self.category_scores['WhatsApp Interaction'] = score
        
        if red_flags > 0:
            self.category_scores['Red Flags Penalty'] = -penalty
        
        return score
    
    def calculate_total_score(self):
        """Calculate final score"""
        auto_score = self.calculate_auto_score()
        quality_score = self.calculate_quality_score()
        interaction_score = self.calculate_interaction_score()
        
        self.score = auto_score + quality_score + interaction_score
        return self.score
    
    def generate_recommendations(self):
        """Generate actionable recommendations"""
        self.recommendations = []
        
        if not self.data.get('has_name'):
            self.recommendations.append("❌ Obtain complete business/individual name")
        if not self.data.get('has_phone'):
            self.recommendations.append("📞 Verify phone number")
        if not self.data.get('has_address'):
            self.recommendations.append("🏠 Request complete address")
        if not self.data.get('has_id_photo'):
            self.recommendations.append("🆔 Require ID photo upload")
        if self.data.get('guarantor_count', 0) < 2:
            self.recommendations.append("👥 Request at least 2 guarantor contacts")
        if self.data.get('registration_type') == 'none':
            self.recommendations.append("📋 Request business registration (CAC/SMEDAN)")
        if not self.data.get('has_supplier_proof'):
            self.recommendations.append("📄 Obtain supplier documentation")
        if not self.data.get('has_operations_proof'):
            self.recommendations.append("🏭 Request proof of business operations")
        if self.data.get('testimonial_quality') in ['suspicious', 'mixed']:
            self.recommendations.append("⭐ Verify customer testimonials authenticity")
        if self.data.get('responsiveness_rating', 5) < 3:
            self.recommendations.append("⏰ Address slow response time concerns")
        if self.data.get('communication_quality') == 'unprofessional':
            self.recommendations.append("💬 Provide communication guidelines")
    
    def identify_risk_factors(self):
        """Identify risk factors"""
        self.risk_factors = []
        
        if self.data.get('red_flags_count', 0) > 0:
            self.risk_factors.append(f"🚩 {self.data.get('red_flags_count')} red flags identified")
        if self.data.get('testimonial_quality') == 'suspicious':
            self.risk_factors.append("⚠️ Suspicious testimonials detected")
        if self.data.get('communication_quality') == 'unprofessional':
            self.risk_factors.append("💬 Unprofessional communication style")
        if self.data.get('responsiveness_rating', 5) == 1:
            self.risk_factors.append("⏰ Very poor responsiveness")
        if not self.data.get('has_id_photo'):
            self.risk_factors.append("🆔 No ID verification completed")
        if self.data.get('registration_type') == 'none':
            self.risk_factors.append("🏢 No business registration on file")
        if self.data.get('id_quality') == 'poor':
            self.risk_factors.append("📸 Poor quality ID documentation")
    
    def get_badge(self):
        """Assign verification badge"""
        if self.score >= 80:
            return {
                'badge': '🟢 Green (Verified)',
                'status': 'APPROVED',
                'description': 'Low risk vendor with strong verification',
                'color': '#10b981'
            }
        elif self.score >= 60:
            return {
                'badge': '🟡 Yellow (Conditional)',
                'status': 'CONDITIONAL',
                'description': 'Medium risk - proceed with caution and monitoring',
                'color': '#f59e0b'
            }
        else:
            return {
                'badge': '🔴 Red (Rejected)',
                'status': 'REJECTED',
                'description': 'High risk - requires significant improvements',
                'color': '#ef4444'
            }

# Header
st.title("🛡️ Vendor Verification System v3.0")
st.markdown("### Comprehensive 3-Step Verification Process")

# Progress indicator
col1, col2, col3 = st.columns(3)
with col1:
    status1 = "✅" if st.session_state.current_step > 1 else "📝" if st.session_state.current_step == 1 else "⏸️"
    st.markdown(f"### {status1} Step 1: Data Entry")
with col2:
    status2 = "✅" if st.session_state.current_step > 2 else "📝" if st.session_state.current_step == 2 else "⏸️"
    st.markdown(f"### {status2} Step 2: Document Review")
with col3:
    status3 = "✅" if st.session_state.current_step > 3 else "📝" if st.session_state.current_step == 3 else "⏸️"
    st.markdown(f"### {status3} Step 3: WhatsApp Assessment")

st.markdown("---")

# STEP 1: DATA ENTRY
if st.session_state.current_step == 1:
    st.markdown('<div class="section-header"><h2>📋 Step 1: Data Entry from Registration Form</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📝 Vendor Information")
        vendor_name = st.text_input("Vendor/Business Name *", key="vendor_name")
        vendor_email = st.text_input("Email Address", key="vendor_email")
        vendor_category = st.selectbox("Business Category", 
            ["", "Electronics", "Fashion", "Food & Beverage", "Services", "Manufacturing", 
             "Beauty", "Health & Wellness", "Transportation & Logistics", "Dropshipping", "Gadget", "Other"],
            key="vendor_category"
        )
        assessment_date = st.date_input("Assessment Date", datetime.now(), key="assessment_date")
        
        st.markdown("#### ✅ Basic Information Provided")
        has_name = st.checkbox("Full name/business name provided", key="has_name")
        has_phone = st.checkbox("Phone number provided", key="has_phone")
        has_address = st.checkbox("Complete address provided", key="has_address")
        has_social_media = st.checkbox("Social media links provided", key="has_social_media")
    
    with col2:
        st.markdown("#### 📎 Documents Submitted")
        has_id_photo = st.checkbox("ID photo + selfie uploaded", key="has_id_photo")
        
        guarantor_count = st.radio(
            "Number of guarantor contacts provided",
            options=[0, 1, 2],
            format_func=lambda x: f"{x} contact(s)" + (" ⚠️ Needs at least 2" if x < 2 else " ✓"),
            key="guarantor_count"
        )
        
        registration_type = st.selectbox(
            "Business registration type",
            ["none", "smedan", "cac"],
            format_func=lambda x: x.upper() if x != "none" else "None - Not Registered",
            key="registration_type"
        )
        
        has_supplier_proof = st.checkbox("Supplier proof documents uploaded", key="has_supplier_proof")
        has_operations_proof = st.checkbox("Operations proof uploaded (photos/videos)", key="has_operations_proof")
        has_testimonials = st.checkbox("Customer testimonials uploaded", key="has_testimonials")
        
        st.markdown("#### 📄 Business Policies")
        has_refund_policy = st.checkbox("Refund/return policy provided", key="has_refund_policy")
        has_delivery_info = st.checkbox("Delivery timeline information provided", key="has_delivery_info")
    
    if st.button("Continue to Document Review →", type="primary", use_container_width=True):
        if not vendor_name:
            st.error("⚠️ Please enter the vendor name before continuing")
        else:
            st.session_state.vendor_data.update({
                'vendor_name': vendor_name,
                'vendor_email': vendor_email,
                'vendor_category': vendor_category,
                'assessment_date': assessment_date,
                'has_name': has_name,
                'has_phone': has_phone,
                'has_address': has_address,
                'has_social_media': has_social_media,
                'has_id_photo': has_id_photo,
                'guarantor_count': guarantor_count,
                'registration_type': registration_type,
                'has_supplier_proof': has_supplier_proof,
                'has_operations_proof': has_operations_proof,
                'has_testimonials': has_testimonials,
                'has_refund_policy': has_refund_policy,
                'has_delivery_info': has_delivery_info
            })
            st.session_state.current_step = 2
            st.rerun()

# STEP 2: DOCUMENT QUALITY REVIEW
elif st.session_state.current_step == 2:
    st.markdown('<div class="section-header"><h2>🔍 Step 2: Document Quality Assessment</h2></div>', unsafe_allow_html=True)
    st.info("📌 Review the quality of uploaded documents and testimonials")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 Document Quality Review")
        
        if st.session_state.vendor_data.get('has_id_photo'):
            id_quality = st.select_slider(
                "ID Photo Quality",
                options=['poor', 'acceptable', 'excellent'],
                value='acceptable',
                key="id_quality"
            )
        else:
            st.warning("⚠️ No ID photo uploaded")
            id_quality = 'poor'
        
        if st.session_state.vendor_data.get('registration_type') != 'none':
            registration_quality = st.select_slider(
                "Registration Documents Quality",
                options=['poor', 'acceptable', 'excellent'],
                value='acceptable',
                key="registration_quality"
            )
        else:
            st.warning("⚠️ No registration documents")
            registration_quality = 'poor'
        
        if st.session_state.vendor_data.get('has_supplier_proof'):
            supplier_quality = st.select_slider(
                "Supplier Proof Quality",
                options=['poor', 'acceptable', 'excellent'],
                value='acceptable',
                key="supplier_quality"
            )
        else:
            st.warning("⚠️ No supplier proof uploaded")
            supplier_quality = 'poor'
    
    with col2:
        if st.session_state.vendor_data.get('has_operations_proof'):
            operations_quality = st.select_slider(
                "Operations Proof Quality",
                options=['poor', 'acceptable', 'excellent'],
                value='acceptable',
                key="operations_quality"
            )
        else:
            st.warning("⚠️ No operations proof uploaded")
            operations_quality = 'poor'
        
        st.markdown("#### ⭐ Testimonial Assessment")
        if st.session_state.vendor_data.get('has_testimonials'):
            testimonial_quality = st.select_slider(
                "Testimonial Authenticity",
                options=['suspicious', 'mixed', 'authentic'],
                value='mixed',
                help="Suspicious: Fake/generic reviews | Mixed: Some legitimate, some questionable | Authentic: Clearly genuine customer feedback",
                key="testimonial_quality"
            )
            st.caption("🔍 Check for generic language, similar writing styles, or unrealistic praise")
        else:
            st.warning("⚠️ No testimonials uploaded")
            testimonial_quality = 'suspicious'
    
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back to Data Entry", use_container_width=True):
            st.session_state.current_step = 1
            st.rerun()
    
    with col_next:
        if st.button("Continue to WhatsApp Assessment →", type="primary", use_container_width=True):
            st.session_state.vendor_data.update({
                'id_quality': id_quality,
                'registration_quality': registration_quality,
                'supplier_quality': supplier_quality,
                'operations_quality': operations_quality,
                'testimonial_quality': testimonial_quality
            })
            st.session_state.current_step = 3
            st.rerun()

# STEP 3: WHATSAPP INTERACTION ASSESSMENT
elif st.session_state.current_step == 3:
    st.markdown('<div class="section-header"><h2>💬 Step 3: WhatsApp Interaction Assessment</h2></div>', unsafe_allow_html=True)
    st.info("📌 Assess vendor's communication after contacting them via WhatsApp")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ⚡ Responsiveness")
        responsiveness_rating = st.slider(
            "Response Speed Rating",
            min_value=1,
            max_value=5,
            value=3,
            help="1 = Very slow (>24h) | 3 = Average (2-24h) | 5 = Very fast (<2h)",
            key="responsiveness_rating"
        )
        
        response_labels = {
            1: "Very Slow (>24 hours)",
            2: "Slow (12-24 hours)",
            3: "Average (2-12 hours)",
            4: "Fast (<2 hours)",
            5: "Very Fast (<30 minutes)"
        }
        st.caption(f"Selected: {response_labels[responsiveness_rating]}")
        
        st.markdown("#### 💬 Communication Quality")
        communication_quality = st.radio(
            "Overall communication style",
            options=['unprofessional', 'professional'],
            format_func=lambda x: x.title(),
            key="communication_quality"
        )
        
        st.caption("Consider: Grammar, tone, clarity, professionalism")
    
    with col2:
        st.markdown("#### 🚩 Red Flags Identified")
        red_flags_count = st.number_input(
            "Number of red flags",
            min_value=0,
            max_value=10,
            value=0,
            help="Issues like inconsistent info, pressure tactics, evasive answers, etc.",
            key="red_flags_count"
        )
        
        if red_flags_count > 0:
            red_flags_notes = st.text_area(
                "Describe the red flags identified",
                placeholder="E.g., Inconsistent business address, pushy sales tactics, avoided questions about suppliers...",
                key="red_flags_notes"
            )
        else:
            red_flags_notes = ""
        
        st.markdown("#### 📝 Additional Notes")
        reviewer_notes = st.text_area(
            "General observations",
            placeholder="Any additional comments about the vendor...",
            key="reviewer_notes"
        )
    
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back to Document Review", use_container_width=True):
            st.session_state.current_step = 2
            st.rerun()
    
    with col_next:
        if st.button("Calculate Final Score & Generate Report →", type="primary", use_container_width=True):
            st.session_state.vendor_data.update({
                'responsiveness_rating': responsiveness_rating,
                'communication_quality': communication_quality,
                'red_flags_count': red_flags_count,
                'red_flags_notes': red_flags_notes,
                'reviewer_notes': reviewer_notes
            })
            
            # Calculate score
            scorer = VendorScorerV3(st.session_state.vendor_data)
            final_score = scorer.calculate_total_score()
            scorer.generate_recommendations()
            scorer.identify_risk_factors()
            badge_info = scorer.get_badge()
            
            st.session_state.final_score = {
                'scorer': scorer,
                'score': final_score,
                'badge_info': badge_info
            }
            st.session_state.current_step = 4
            st.rerun()

# STEP 4: RESULTS & CERTIFICATE
elif st.session_state.current_step == 4:
    scorer = st.session_state.final_score['scorer']
    final_score = st.session_state.final_score['score']
    badge_info = st.session_state.final_score['badge_info']
    vendor_data = st.session_state.vendor_data
    
    # Results header
    st.markdown('<div class="section-header"><h2>📊 Final Assessment Results</h2></div>', unsafe_allow_html=True)
    
    # Score display
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="score-display">{final_score}/100</div>
            <div style="font-size: 1.5rem; margin-top: 0.5rem;">{badge_info['badge']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.metric("Status", badge_info['status'])
        st.caption(badge_info['description'])
    
    with col3:
        st.metric("Vendor", vendor_data.get('vendor_name', 'N/A'))
        st.caption(f"Category: {vendor_data.get('vendor_category', 'N/A')}")
    
    # Category breakdown
    st.markdown("### 📈 Score Breakdown")
    
    breakdown_data = []
    max_scores = {
        'Basic Information': 15,
        'Documents Submitted': 25,
        'Document Quality': 35,
        'WhatsApp Interaction': 25
    }
    
    for category, score in scorer.category_scores.items():
        if category != 'Red Flags Penalty':
            max_score = max_scores.get(category, 0)
            breakdown_data.append({
                'Category': category,
                'Score': score,
                'Max': max_score,
                'Percentage': f"{(score/max_score*100):.1f}%" if max_score > 0 else "N/A"
            })
    
    df_breakdown = pd.DataFrame(breakdown_data)
    
    for _, row in df_breakdown.iterrows():
        col_label, col_bar = st.columns([1, 3])
        with col_label:
            st.write(f"**{row['Category']}**")
            st.caption(f"{row['Score']:.1f}/{row['Max']} ({row['Percentage']})")
        with col_bar:
            progress = min(row['Score'] / row['Max'], 1.0) if row['Max'] > 0 else 0
            st.progress(progress)
    
    # Recommendations and Risk Factors
    col_rec, col_risk = st.columns(2)
    
    with col_rec:
        st.markdown("### 💡 Recommendations")
        if scorer.recommendations:
            for rec in scorer.recommendations:
                st.markdown(f"- {rec}")
        else:
            st.success("✅ All verification criteria met!")
    
    with col_risk:
        st.markdown("### ⚠️ Risk Factors")
        if scorer.risk_factors:
            for risk in scorer.risk_factors:
                st.markdown(f"- {risk}")
        else:
            st.success("✅ No significant risks identified!")
    
    # Export options
    st.markdown("---")
    st.markdown("### 📥 Download Assessment Report")
    
    # Logo and signature upload
    col_logo, col_sig = st.columns(2)
    with col_logo:
        uploaded_logo = st.file_uploader(
            "Company Logo (Optional)",
            type=['png', 'jpg', 'jpeg'],
            help="For certificate branding"
        )
    with col_sig:
        uploaded_signature = st.file_uploader(
            "Signature Image (Optional)",
            type=['png', 'jpg', 'jpeg'],
            help="For certificate authorization"
        )
    
    # Generate logo and signature HTML
    logo_html = ""
    if uploaded_logo:
        import base64
        logo_bytes = uploaded_logo.getvalue()
        logo_b64 = base64.b64encode(logo_bytes).decode()
        logo_html = f'<img src="data:image/{uploaded_logo.type.split("/")[1]};base64,{logo_b64}" alt="Company Logo" class="logo">'
    
    signature_html = ""
    if uploaded_signature:
        import base64
        sig_bytes = uploaded_signature.getvalue()
        sig_b64 = base64.b64encode(sig_bytes).decode()
        signature_html = f'<img src="data:image/{uploaded_signature.type.split("/")[1]};base64,{sig_b64}" alt="Signature" style="max-height: 60px; max-width: 200px; display: block; margin: 10px auto;">'
    
    # Generate certificate HTML
    certificate_color = badge_info['color']
    status_icon = "🟢" if 'Green' in badge_info['badge'] else "🟡" if 'Yellow' in badge_info['badge'] else "🔴"
    
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
            }}
            
            .certificate-title {{
                font-size: 22px !important;
                font-weight: 700 !important;
                margin-bottom: 8px;
                color: white !important;
            }}
            
            .certificate-subtitle {{
                font-size: 14px !important;
                font-weight: 300;
                color: white !important;
            }}
            
            .vendor-info {{
                text-align: center;
                margin-bottom: 20px;
                padding: 20px;
                background: #f8f9fa !important;
                border: 2px solid {certificate_color} !important;
                border-radius: 6px;
            }}
            
            .vendor-name {{
                font-size: 24px !important;
                font-weight: 700 !important;
                color: #000 !important;
                margin-bottom: 8px;
                text-transform: uppercase;
            }}
            
            .score-display {{
                font-size: 36px !important;
                font-weight: 700 !important;
                color: {certificate_color} !important;
                text-align: center;
                margin: 15px 0;
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
            }}
            
            .assessment-grid {{
                display: table;
                width: 100%;
                margin: 20px 0;
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
            }}
            
            .section-title {{
                font-size: 16px !important;
                font-weight: 600 !important;
                color: #000 !important;
                margin-bottom: 10px;
                border-bottom: 2px solid {certificate_color} !important;
                padding-bottom: 5px;
            }}
            
            .category-score {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #ddd;
                font-weight: 500;
                color: #000 !important;
            }}
            
            .score-value {{
                color: {certificate_color} !important;
                font-weight: 700 !important;
            }}
            
            .list-item {{
                padding: 6px 0;
                color: #333 !important;
                font-size: 11px;
                border-bottom: 1px dotted #ccc;
            }}
            
            .certificate-footer {{
                background: #f8f9fa !important;
                padding: 20px;
                text-align: center;
                border-top: 3px solid {certificate_color} !important;
                margin-top: 20px;
                border-radius: 6px;
            }}
        </style>
    </head>
    <body>
        <div class="certificate-container">
            <div class="header">
                {logo_html}
                <h1 class="certificate-title">VENDOR VERIFICATION CERTIFICATE</h1>
                <p class="certificate-subtitle">Official Assessment & Compliance Verification v3.0</p>
            </div>
            
            <div class="vendor-info">
                <div class="vendor-name">{vendor_data['vendor_name']}</div>
                <div>{vendor_data['vendor_category']} • Assessed on {vendor_data['assessment_date']}</div>
            </div>
            
            <div style="text-align: center;">
                <div class="score-display">{final_score:.1f}/100</div>
                <div class="status-badge">{badge_info['badge']}</div>
                <p style="color: #64748b; font-style: italic; margin-top: 10px;">{badge_info['description']}</p>
            </div>
            
            <div class="assessment-grid">
                <div class="assessment-section">
                    <h3 class="section-title">📊 Category Scores</h3>
                    {''.join([f'<div class="category-score"><span>{cat}</span><span class="score-value">{score:.1f}/{max_scores.get(cat, 0)}</span></div>' for cat, score in scorer.category_scores.items() if cat != 'Red Flags Penalty'])}
                </div>
                
                <div class="assessment-section">
                    <h3 class="section-title">💡 Key Recommendations</h3>
                    {''.join([f'<div class="list-item">{rec}</div>' for rec in scorer.recommendations[:6]]) if scorer.recommendations else '<p style="color: #059669; font-weight: 600;">All verification criteria met!</p>'}
                </div>
            </div>
            
            {'<div class="assessment-section" style="margin-top: 15px; display: block;"><h3 class="section-title">⚠️ Risk Factors</h3>' + ''.join([f'<div class="list-item">{risk}</div>' for risk in scorer.risk_factors]) + '</div>' if scorer.risk_factors else ''}
            
            <div class="certificate-footer">
                {signature_html if signature_html else '<div style="height: 2px; width: 150px; background: #333; margin: 15px auto;"></div>'}
                <p style="font-weight: 600; margin-top: 10px;">Authorized Verification Officer</p>
                <p style="margin-top: 15px; color: #64748b; font-weight: 500;">
                    Generated by ZOLARUX Vendor Verification System v3.0
                </p>
                <p style="color: #94a3b8; font-size: 11px; margin-top: 8px;">
                    Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                </p>
                <p style="font-family: 'Courier New'; color: #666; font-size: 10px; margin-top: 10px;">
                    Certificate ID: ZLX-{hash(str(vendor_data)) % 100000:05d}
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Download buttons
    col_json, col_html, col_csv = st.columns(3)
    
    # Prepare summary data
    summary_data = {
        'vendor_name': vendor_data['vendor_name'],
        'vendor_email': vendor_data.get('vendor_email', 'N/A'),
        'vendor_category': vendor_data['vendor_category'],
        'assessment_date': str(vendor_data['assessment_date']),
        'total_score': final_score,
        'badge': badge_info['badge'],
        'status': badge_info['status'],
        'category_scores': {k: v for k, v in scorer.category_scores.items()},
        'recommendations': scorer.recommendations,
        'risk_factors': scorer.risk_factors,
        'red_flags_notes': vendor_data.get('red_flags_notes', ''),
        'reviewer_notes': vendor_data.get('reviewer_notes', '')
    }
    
    with col_json:
        json_string = json.dumps(summary_data, indent=2, default=str)
        st.download_button(
            label="📄 JSON Report",
            data=json_string,
            file_name=f"vendor_assessment_{vendor_data['vendor_name']}_{vendor_data['assessment_date']}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_html:
        st.download_button(
            label="🏆 Certificate (HTML)",
            data=html_report,
            file_name=f"vendor_certificate_{vendor_data['vendor_name']}_{vendor_data['assessment_date']}.html",
            mime="text/html",
            use_container_width=True
        )
    
    with col_csv:
        csv_data = f"Vendor Assessment Report v3.0\n"
        csv_data += f"Vendor Name,{vendor_data['vendor_name']}\n"
        csv_data += f"Category,{vendor_data['vendor_category']}\n"
        csv_data += f"Assessment Date,{vendor_data['assessment_date']}\n"
        csv_data += f"Total Score,{final_score:.1f}/100\n"
        csv_data += f"Status,{badge_info['status']}\n\n"
        csv_data += "Category Scores\n"
        for cat, score in scorer.category_scores.items():
            csv_data += f"{cat},{score:.1f}\n"
        
        st.download_button(
            label="📊 CSV Export",
            data=csv_data,
            file_name=f"vendor_assessment_{vendor_data['vendor_name']}_{vendor_data['assessment_date']}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    st.info("💡 **Tip**: Open the HTML certificate in Chrome/Edge, press Ctrl+P, enable 'Background graphics', and save as PDF for best results.")
    
    # Reset button
    if st.button("🔄 Start New Assessment", use_container_width=True):
        st.session_state.current_step = 1
        st.session_state.vendor_data = {}
        st.session_state.final_score = None
        st.rerun()

# Footer
st.markdown("---")
st.markdown("*ZOLARUX Vendor Verification System v3.0 - Built for accuracy and efficiency*")

