import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import base64

# Page config
st.set_page_config(
    page_title="Zolarux Vendor Verification Tool",
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
    .metric-card-initial {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
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
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'vendor_data' not in st.session_state:
    st.session_state.vendor_data = {}
if 'final_result' not in st.session_state:
    st.session_state.final_result = None

# --- SIDEBAR: MODE SELECTION ---
with st.sidebar:
    st.image("https://zolarux.com.ng/images/logo.png", width=150)
    st.title("Admin Controls")
    
    # The Mode Switch
    verification_mode_selection = st.radio(
        "Verification Mode",
        options=["INITIAL (WhatsApp)", "FULL (Platform)"],
        index=0,
        help="INITIAL: Fast check for WhatsApp access. FULL: Detailed scoring for loans & platform benefits."
    )
    
    # Store mode in simple variable for logic checks
    MODE = "INITIAL" if "INITIAL" in verification_mode_selection else "FULL"
    st.session_state.verification_mode = MODE
    
    st.info(f"Currently running: **{MODE} VERIFICATION**")
    if MODE == "INITIAL":
        st.caption("✅ Fast Track\n✅ Pass/Fail Only\n✅ 30-Day Validity")
    else:
        st.caption("🛡️ Deep Dive\n🛡️ 100-Point Score\n🛡️ Long-term Trust")

# Scoring & Logic Class
class VendorScorerV3:
    def __init__(self, data, mode="FULL"):
        self.data = data
        self.mode = mode
        self.score = 0
        self.category_scores = {}
        self.recommendations = []
        self.risk_factors = []
    
    # --- LOGIC FOR INITIAL MODE ---
    def assess_initial_verification(self):
        """Binary Pass/Fail logic for WhatsApp verification"""
        checks = []
        
        # 1. Critical Data Presence
        if not self.data.get('has_name'): checks.append("Missing Business Name")
        if not self.data.get('has_phone'): checks.append("Missing Phone Number")
        if not self.data.get('has_location'): checks.append("Missing Location")
        if not self.data.get('has_id_photo'): checks.append("Missing ID Verification")
        if not self.data.get('has_supplier_proof') and not self.data.get('has_operations_proof'): 
            checks.append("No Proof of Stock/Operations")
        
        # 2. Process Compliance
        if not self.data.get('agreed_to_rules'): checks.append("Did not agree to Escrow Rules")
        if not self.data.get('video_call_verified'): checks.append("Video Call Not Completed")
        
        # 3. Behavioral Flags
        if self.data.get('red_flags_count', 0) > 0: checks.append(f"Found {self.data.get('red_flags_count')} Red Flags")
        if self.data.get('responsiveness_rating', 3) < 2: checks.append("Responsiveness too low")

        # Result
        passed = len(checks) == 0
        
        return {
            'passed': passed,
            'issues': checks,
            'badge': '🔵 WhatsApp Verified' if passed else '🔴 Verification Failed',
            'status': 'PROVISIONALLY VERIFIED' if passed else 'FAILED',
            'description': 'Valid for 30 Days. Subject to Full Verification.',
            'color': '#2563eb' if passed else '#ef4444'
        }

    # --- LOGIC FOR FULL MODE (Existing 100-Point System) ---
    def calculate_auto_score(self):
        score = 0
        # Basic Info (15 pts)
        if self.data.get('has_name'): score += 3
        if self.data.get('has_phone'): score += 4
        if self.data.get('has_address'): score += 4
        if self.data.get('has_social_media'): score += 4
        self.category_scores['Basic Information'] = score
        
        # Documents (25 pts)
        doc_score = 0
        if self.data.get('has_id_photo'): doc_score += 5
        doc_score += self.data.get('guarantor_count', 0) * 2.5
        reg_points = {'none': 0, 'smedan': 3, 'cac': 5}
        doc_score += reg_points.get(self.data.get('registration_type', 'none'), 0)
        if self.data.get('has_supplier_proof'): doc_score += 5
        if self.data.get('has_operations_proof'): doc_score += 5
        if self.data.get('has_testimonials'): doc_score += 2.5
        self.category_scores['Documents Submitted'] = doc_score
        score += doc_score
        return score
    
    def calculate_quality_score(self):
        quality_points = {'poor': 1, 'acceptable': 3, 'excellent': 5}
        score = 0
        score += quality_points.get(self.data.get('id_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('registration_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('supplier_quality', 'poor'), 0)
        score += quality_points.get(self.data.get('operations_quality', 'poor'), 0)
        
        testimonial_points = {'suspicious': 0, 'mixed': 5, 'authentic': 10}
        score += testimonial_points.get(self.data.get('testimonial_quality', 'suspicious'), 0)
        
        if self.data.get('has_refund_policy'): score += 2.5
        if self.data.get('has_delivery_info'): score += 2.5
        
        self.category_scores['Document Quality'] = score
        return score
    
    def calculate_interaction_score(self):
        score = 0
        score += self.data.get('responsiveness_rating', 1) * 2
        comm_points = {'unprofessional': 0, 'professional': 10}
        score += comm_points.get(self.data.get('communication_quality', 'unprofessional'), 0)
        
        red_flags = self.data.get('red_flags_count', 0)
        penalty = min(red_flags * 5, score)
        score -= penalty
        
        self.category_scores['WhatsApp Interaction'] = score
        if red_flags > 0: self.category_scores['Red Flags Penalty'] = -penalty
        return score

    def calculate_total_score(self):
        if self.mode == "INITIAL":
            return None # Initial mode doesn't use scores
            
        auto_score = self.calculate_auto_score()
        quality_score = self.calculate_quality_score()
        interaction_score = self.calculate_interaction_score()
        self.score = auto_score + quality_score + interaction_score
        return self.score

    def get_full_badge(self):
        if self.score >= 80:
            return {'badge': '🟢 Green (Verified)', 'status': 'APPROVED', 'description': 'Low risk. Eligible for Loans.', 'color': '#10b981'}
        elif self.score >= 60:
            return {'badge': '🟡 Yellow (Conditional)', 'status': 'CONDITIONAL', 'description': 'Medium risk. Monitor closely.', 'color': '#f59e0b'}
        else:
            return {'badge': '🔴 Red (Rejected)', 'status': 'REJECTED', 'description': 'High risk. Do not onboard.', 'color': '#ef4444'}

# Header
st.title("🛡️ Zolarux Verification")
if MODE == "INITIAL":
    st.markdown("### 🔵 Mode: Initial WhatsApp Verification (Fast-Track)")
else:
    st.markdown("### 🟢 Mode: Full Platform Verification (Deep-Dive)")

# Progress indicator
col1, col2, col3 = st.columns(3)
with col1:
    status1 = "✅" if st.session_state.current_step > 1 else "📝" if st.session_state.current_step == 1 else "⏸️"
    st.markdown(f"### {status1} Data Collection")
with col2:
    status2 = "✅" if st.session_state.current_step > 2 else "📝" if st.session_state.current_step == 2 else "⏸️"
    st.markdown(f"### {status2} Validation")
with col3:
    status3 = "✅" if st.session_state.current_step > 3 else "📝" if st.session_state.current_step == 3 else "⏸️"
    st.markdown(f"### {status3} Decision")

st.markdown("---")

# ==========================================
# STEP 1: DATA ENTRY
# ==========================================
if st.session_state.current_step == 1:
    st.markdown(f'<div class="section-header"><h2>📋 Step 1: {MODE} Data Collection</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📝 Vendor Identity")
        vendor_name = st.text_input("Business/Vendor Name *", key="vendor_name")
        vendor_phone = st.text_input("Phone Number *", key="vendor_phone")
        
        # New: Location is critical for Initial
        vendor_location = st.text_input("Location (City/State) *", key="vendor_location")
        
        vendor_category = st.selectbox("Category", 
            ["", "Electronics", "Fashion", "Beauty", "Services", "Dropshipping", "Gadgets", "Other"],
            key="vendor_category"
        )
        
        # Only ask for Email in FULL mode, optional in INITIAL
        if MODE == "FULL":
            vendor_email = st.text_input("Email Address", key="vendor_email")
        else:
            vendor_email = "N/A (Initial)"
            
        assessment_date = st.date_input("Assessment Date", datetime.now(), key="assessment_date")
        
        st.markdown("#### ✅ Verification Checks")
        has_name = st.checkbox("Name Provided", value=True, key="has_name")
        has_phone = st.checkbox("Phone Validated", value=True, key="has_phone")
        has_location = st.checkbox("Location Provided", value=True, key="has_location")
        
        # Address is full address in Full mode
        if MODE == "FULL":
            has_address = st.checkbox("Full Address Verified", key="has_address")
            has_social_media = st.checkbox("Social Media Links", key="has_social_media")
        else:
            has_address = True # Assumed covered by location in initial
            has_social_media = st.checkbox("Social Media (Optional)", key="has_social_media")

    with col2:
        st.markdown("#### 📎 Proofs Submitted")
        has_id_photo = st.checkbox("Valid ID (NIN/Voter/Passport) *", key="has_id_photo")
        
        # Simplified proof for Initial
        st.markdown("**Proof of Stock / Operations**")
        has_supplier_proof = st.checkbox("Supplier/Stock Proof (Video/Pic)", key="has_supplier_proof")
        has_operations_proof = st.checkbox("Past Operations (Waybills/Chats)", key="has_operations_proof")
        
        has_testimonials = st.checkbox("Customer Testimonials", key="has_testimonials")
        
        # INITIAL SPECIFIC CHECKS
        st.markdown("#### 🤝 Agreements")
        agreed_to_rules = st.checkbox("Agreed to Escrow Rules *", key="agreed_to_rules")
        video_call_verified = st.checkbox("Video Call Verification Passed *", key="video_call_verified")

        # FULL MODE EXTRAS (Hidden in Initial)
        if MODE == "FULL":
            st.markdown("---")
            st.markdown("#### 🟢 Full Verification Extras")
            guarantor_count = st.radio("Guarantors", [0, 1, 2], key="guarantor_count")
            registration_type = st.selectbox("Registration", ["none", "smedan", "cac"], key="registration_type")
            has_refund_policy = st.checkbox("Refund Policy", key="has_refund_policy")
            has_delivery_info = st.checkbox("Delivery Info", key="has_delivery_info")
        else:
            # Default values for Initial mode to prevent errors
            guarantor_count = 0
            registration_type = "none"
            has_refund_policy = False
            has_delivery_info = False

    if st.button("Continue →", type="primary", use_container_width=True):
        if not vendor_name or not vendor_phone:
            st.error("⚠️ Business Name and Phone are required.")
        else:
            # Save to session
            st.session_state.vendor_data.update({
                'vendor_name': vendor_name, 'vendor_phone': vendor_phone, 
                'vendor_location': vendor_location, 'vendor_email': vendor_email,
                'vendor_category': vendor_category, 'assessment_date': assessment_date,
                'has_name': has_name, 'has_phone': has_phone, 'has_location': has_location,
                'has_address': has_address, 'has_social_media': has_social_media,
                'has_id_photo': has_id_photo, 'has_supplier_proof': has_supplier_proof,
                'has_operations_proof': has_operations_proof, 'has_testimonials': has_testimonials,
                'agreed_to_rules': agreed_to_rules, 'video_call_verified': video_call_verified,
                'guarantor_count': guarantor_count, 'registration_type': registration_type,
                'has_refund_policy': has_refund_policy, 'has_delivery_info': has_delivery_info
            })
            st.session_state.current_step = 2
            st.rerun()

# ==========================================
# STEP 2: DOCUMENT REVIEW
# ==========================================
elif st.session_state.current_step == 2:
    st.markdown('<div class="section-header"><h2>🔍 Step 2: Quality Review</h2></div>', unsafe_allow_html=True)
    
    if MODE == "INITIAL":
        st.info("ℹ️ **INITIAL MODE:** Simplified review. Ensure documents look legitimate. No granular scoring.")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**ID Card Status:**")
            id_quality = st.radio("ID Legibility", ["Clear", "Blurry/Fake"], key="id_quality_init")
        with col2:
            st.write("**Stock Proof Status:**")
            stock_quality = st.radio("Stock/Ops Proof", ["Convincing", "Suspicious"], key="stock_quality_init")
            
        # Map simple inputs to complex keys for backend compatibility
        id_q = 'excellent' if id_quality == 'Clear' else 'poor'
        sup_q = 'excellent' if stock_quality == 'Convincing' else 'poor'
        
        # Defaults for ignored fields
        registration_quality = 'poor'
        operations_quality = sup_q
        supplier_quality = sup_q
        testimonial_quality = 'mixed'

    else:
        # FULL MODE SLIDERS
        st.info("📌 **FULL MODE:** Detailed quality scoring for credit worthiness.")
        col1, col2 = st.columns(2)
        with col1:
            id_q = st.select_slider("ID Quality", ['poor', 'acceptable', 'excellent'], value='acceptable', key="id_q")
            registration_quality = st.select_slider("Reg Doc Quality", ['poor', 'acceptable', 'excellent'], value='acceptable', key="reg_q")
            supplier_quality = st.select_slider("Supplier Proof Quality", ['poor', 'acceptable', 'excellent'], value='acceptable', key="sup_q")
        with col2:
            operations_quality = st.select_slider("Ops Proof Quality", ['poor', 'acceptable', 'excellent'], value='acceptable', key="ops_q")
            testimonial_quality = st.select_slider("Testimonial Auth", ['suspicious', 'mixed', 'authentic'], value='mixed', key="test_q")

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back"):
            st.session_state.current_step = 1
            st.rerun()
    with col_next:
        if st.button("Continue →", type="primary"):
            st.session_state.vendor_data.update({
                'id_quality': id_q,
                'registration_quality': registration_quality,
                'supplier_quality': supplier_quality,
                'operations_quality': operations_quality if MODE == "FULL" else sup_q,
                'testimonial_quality': testimonial_quality if MODE == "FULL" else 'mixed'
            })
            st.session_state.current_step = 3
            st.rerun()

# ==========================================
# STEP 3: INTERACTION ASSESSMENT
# ==========================================
elif st.session_state.current_step == 3:
    st.markdown('<div class="section-header"><h2>💬 Step 3: Interaction & Risk</h2></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### ⚡ Responsiveness")
        responsiveness_rating = st.slider("Response Speed (1=Slow, 5=Fast)", 1, 5, 3, key="resp_rate")
        
        st.markdown("#### 💬 Communication")
        communication_quality = st.radio("Style", ['unprofessional', 'professional'], index=1, format_func=lambda x: x.title(), key="comm_q")
    
    with col2:
        st.markdown("#### 🚩 Red Flags (Crucial)")
        red_flags_count = st.number_input("Count of Red Flags", 0, 10, 0, help="Evasive answers, pressure tactics, mismatched names", key="red_flags")
        
        if red_flags_count > 0:
            red_flags_notes = st.text_area("Describe Red Flags", placeholder="E.g. Name on ID different from Bank Name", key="rf_notes")
        else:
            red_flags_notes = "None"
            
        reviewer_notes = st.text_area("Internal Notes", placeholder="General impression...", key="rev_notes")

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back"):
            st.session_state.current_step = 2
            st.rerun()
    
    with col_next:
        if st.button("Generate Decision →", type="primary"):
            st.session_state.vendor_data.update({
                'responsiveness_rating': responsiveness_rating,
                'communication_quality': communication_quality,
                'red_flags_count': red_flags_count,
                'red_flags_notes': red_flags_notes,
                'reviewer_notes': reviewer_notes
            })
            
            # RUN LOGIC
            scorer = VendorScorerV3(st.session_state.vendor_data, mode=MODE)
            
            if MODE == "INITIAL":
                result = scorer.assess_initial_verification()
                st.session_state.final_result = result
            else:
                final_score = scorer.calculate_total_score()
                scorer.generate_recommendations()
                scorer.identify_risk_factors()
                badge_info = scorer.get_full_badge()
                st.session_state.final_result = {
                    'scorer': scorer,
                    'score': final_score,
                    'badge_info': badge_info,
                    'passed': final_score >= 60 # Arbitrary pass mark for full logic
                }
                
            st.session_state.current_step = 4
            st.rerun()

# ==========================================
# STEP 4: FINAL RESULT & CERTIFICATE
# ==========================================
elif st.session_state.current_step == 4:
    res = st.session_state.final_result
    data = st.session_state.vendor_data
    
    st.markdown(f'<div class="section-header"><h2>📊 Final Decision: {MODE}</h2></div>', unsafe_allow_html=True)

    # --- RESULTS DASHBOARD (Same as before) ---
    scorer = res['scorer'] if MODE == "FULL" else None
    badge = res['badge_info'] if MODE == "FULL" else {'badge': res['badge'], 'color': res['color'], 'status': res['status']}
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="background: {badge['color']}">
            <div class="score-display">{res.get('score', 'PASS') if MODE == 'FULL' else ''}</div>
            <div style="font-size: 1.5rem;">{badge['badge']}</div>
            <div>{badge['status']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if MODE == "FULL":
            st.write("**Risk Analysis**")
            if scorer.risk_factors:
                for risk in scorer.risk_factors:
                    st.write(f"- {risk}")
            else:
                st.write("No major risks found.")
        else:
            st.write("**Initial Check**")
            if res.get('passed'):
                st.success("Requirements Met")
            else:
                st.error("Requirements Failed")

    # --- CERTIFICATE GENERATION ---
    st.markdown("---")
    st.markdown("### 📥 Download Certificate")
    
    # 1. Customization
    with st.expander("🎨 Customize Certificate (Logo & Signature)", expanded=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            uploaded_logo = st.file_uploader("Upload Company Logo", type=['png', 'jpg', 'jpeg'], key="cert_logo")
        with col_c2:
            uploaded_sig = st.file_uploader("Upload Authorized Signature", type=['png', 'jpg', 'jpeg'], key="cert_sig")

    # --- PDF GENERATOR FUNCTION ---
    from fpdf import FPDF
    import tempfile

    def create_pdf(vendor_data, mode, badge_data, score, logo_file, sig_file):
        class PDF(FPDF):
            def header(self):
                # Header Color Strip
                self.set_fill_color(int(badge_data['color'][1:3], 16), int(badge_data['color'][3:5], 16), int(badge_data['color'][5:7], 16))
                self.rect(0, 0, 210, 40, 'F')
                self.ln(30)

        pdf = PDF()
        pdf.add_page()
        
        # 1. Logo Handling
        if logo_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
                tmp_logo.write(logo_file.getvalue())
                pdf.image(tmp_logo.name, x=10, y=8, h=25)

        # 2. Title
        pdf.set_font('Arial', 'B', 24)
        pdf.set_text_color(255, 255, 255)
        title = "PROVISIONAL PASS" if mode == "INITIAL" else "VENDOR CERTIFICATE"
        pdf.cell(0, -20, title, 0, 1, 'C')
        
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 30, "Zolarux Trust Infrastructure", 0, 1, 'C')
        
        pdf.ln(20) # Spacer

        # 3. Vendor Info
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, "This document certifies that", 0, 1, 'C')
        
        pdf.set_font('Arial', 'B', 30)
        pdf.cell(0, 20, vendor_data['vendor_name'].upper(), 0, 1, 'C')
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Category: {vendor_data['vendor_category']}", 0, 1, 'C')
        
        pdf.ln(10)

        # 4. Badge/Status
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font('Arial', 'B', 16)
        # Check if score exists (FULL mode)
        score_text = f"Trust Score: {score}/100" if mode == "FULL" else "Status: VERIFIED"
        pdf.cell(0, 15, score_text, 0, 1, 'C', True)
        
        pdf.set_text_color(int(badge_data['color'][1:3], 16), int(badge_data['color'][3:5], 16), int(badge_data['color'][5:7], 16))
        pdf.cell(0, 15, badge_data['status'], 0, 1, 'C')
        
        pdf.ln(10)

        # 5. Details Table (Simple Text for PDF)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Verification Details:", 0, 1, 'L')
        pdf.set_font('Arial', '', 11)
        
        # Verification points
        checks = [
            f"Phone: {vendor_data['vendor_phone']}",
            f"Location: {vendor_data['vendor_location']}",
            f"ID Verified: {'Yes' if vendor_data['has_id_photo'] else 'No'}",
            f"Stock/Ops Proof: {'Yes' if vendor_data['has_supplier_proof'] or vendor_data['has_operations_proof'] else 'No'}"
        ]
        
        for check in checks:
            pdf.cell(0, 8, f"- {check}", 0, 1, 'L')

        pdf.ln(10)
        
        # 6. Signature Area
        pdf.set_draw_color(150, 150, 150)
        pdf.line(60, 250, 150, 250) # Line
        
        if sig_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sig:
                tmp_sig.write(sig_file.getvalue())
                # Center signature roughly
                pdf.image(tmp_sig.name, x=85, y=230, h=20)
                
        pdf.set_y(255)
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 5, "Authorized Verification Officer", 0, 1, 'C')
        
        # Footer ID
        pdf.set_font('Courier', '', 8)
        pdf.set_text_color(100, 100, 100)
        cert_id = f"ZLX-{hash(vendor_data['vendor_name']) % 10000:04d}"
        pdf.cell(0, 10, f"Certificate ID: {cert_id} | Generated: {datetime.now().strftime('%Y-%m-%d')}", 0, 1, 'C')

        return pdf.output(dest='S').encode('latin-1')

    # --- RENDER DOWNLOAD BUTTON ---
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        # We need to capture the file buffers before generating PDF
        if st.button("📄 Generate PDF Certificate"):
            if not uploaded_logo:
                st.warning("⚠️ For a professional PDF, please upload a logo first.")
            
            try:
                pdf_bytes = create_pdf(
                    data, 
                    MODE, 
                    badge, 
                    res.get('score', 0), 
                    uploaded_logo, 
                    uploaded_sig
                )
                
                # Setup download in session state to persist it
                st.session_state.pdf_bytes = pdf_bytes
                st.success("PDF Generated! Click download below.")
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
                st.info("Ensure you have installed fpdf: `pip install fpdf`")

    with col_d2:
        if 'pdf_bytes' in st.session_state:
            st.download_button(
                label="⬇️ Download PDF Now",
                data=st.session_state.pdf_bytes,
                file_name=f"Zolarux_Cert_{data['vendor_name']}.pdf",
                mime="application/pdf"
            )

    if st.button("🔄 Start New Assessment"):
        st.session_state.current_step = 1
        st.session_state.vendor_data = {}
        if 'pdf_bytes' in st.session_state: del st.session_state.pdf_bytes
        st.rerun()


