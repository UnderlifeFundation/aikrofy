"""
Krof Intelligence Engine - AI Powered Email & Messaging Personalization Service
Generates personalized, high-converting HTML emails for:
1. Internal Platform Lifecycle (Waitlist Onboarding, Access Approval, Credit Alerts)
2. Tenant Companies -> Prospects (Outbound Campaign Copy, Personal Recommendations)
"""
import logging
import json
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class KrofAgentService:
    """
    AI Communication & Copywriting Agent ("Krof")
    Customizes email styling, layout, and content based on recipient profile and platform context.
    """

    @staticmethod
    def _build_html_template(
        header_title: str,
        badge_text: str,
        badge_color: str,
        main_content_html: str,
        cta_text: Optional[str] = None,
        cta_url: Optional[str] = None,
        footer_text: Optional[str] = None
    ) -> str:
        """Generates a responsive HTML email layout with Aikrofy's design system."""
        cta_button = ""
        if cta_text and cta_url:
            cta_button = f"""
            <div style="text-align: center; margin: 30px 0;">
                <a href="{cta_url}" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35); transition: all 0.2s ease;">
                    {cta_text}
                </a>
            </div>
            """

        footer = footer_text or "Aikrofy Inc. • Plataforma de Agentes Conversacionales IA"

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{header_title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed;">
        <tr>
            <td align="center" style="padding: 40px 15px;">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01); border: 1px solid #e2e8f0;">
                    <!-- Header Bar -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 32px 40px; text-align: left;">
                            <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td>
                                        <span style="font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">Aikrofy<span style="color: #6366f1;">.com</span></span>
                                    </td>
                                    <td align="right">
                                        <span style="background-color: {badge_color}; color: #ffffff; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 5px 12px; border-radius: 20px; letter-spacing: 0.5px;">{badge_text}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Content Body -->
                    <tr>
                        <td style="padding: 36px 40px 24px 40px;">
                            <h1 style="margin: 0 0 20px 0; font-size: 22px; font-weight: 700; color: #0f172a; line-height: 1.3;">{header_title}</h1>
                            
                            <div style="font-size: 15px; line-height: 1.6; color: #334155;">
                                {main_content_html}
                            </div>
                            
                            {cta_button}
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f1f5f9; padding: 24px 40px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #64748b;">
                            <p style="margin: 0 0 8px 0;">{footer}</p>
                            <p style="margin: 0;"><a href="https://aikrofy.com" style="color: #4f46e5; text-decoration: none;">www.aikrofy.com</a> • Centro de Soporte e Inteligencia Artificial</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    @classmethod
    def generate_waitlist_confirmation_email(cls, lead_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Uses Krof AI logic to compose a personalized waitlist confirmation email
        reflecting the prospect's industry and AI expectations.
        """
        contact_name = lead_data.get('contact_name', 'Estimado/a')
        company_name = lead_data.get('company_name', 'su empresa')
        industry = lead_data.get('industry', 'su sector')
        ai_expectations = lead_data.get('ai_expectations', '')

        # AI Customization Insight
        ai_insight = f"Analizando tu sector <strong>{industry}</strong>, asignaremos a tu cuenta un agente especializado para optimizar las interacciones en {company_name}."
        if ai_expectations:
            ai_insight += f"<br><br><em>Nota para nuestro equipo de onboarding:</em> Tomamos en cuenta tu objetivo prioritario: <em>'{ai_expectations}'</em>."

        subject = f"🚀 [Aikrofy] Confirmación de registro para {company_name}"
        
        main_content = f"""
        <p>Hola <strong>{contact_name}</strong>,</p>
        <p>Gracias por registrarte en la fase Beta de <strong>Aikrofy</strong>. Hemos recibido exitosamente la solicitud para <strong>{company_name}</strong>.</p>
        
        <div style="background-color: #f8fafc; border-left: 4px solid #6366f1; padding: 18px; margin: 24px 0; border-radius: 6px;">
            <p style="margin: 0 0 8px 0; font-weight: 700; color: #1e1b4b; font-size: 14px; text-transform: uppercase;">🔍 Diagnóstico Inicial de Krof Engine:</p>
            <p style="margin: 0; font-size: 14px; color: #334155;">{ai_insight}</p>
        </div>
        
        <p>Nuestro equipo evalúa las solicitudes de la lista de espera prioritariamente. Tan pronto como tu acceso sea autorizado, recibirás tus credenciales privadas y créditos de prueba iniciales.</p>
        """

        html_body = cls._build_html_template(
            header_title=f"¡Registro recibido para {company_name}!",
            badge_text="En Revisión",
            badge_color="#6366f1",
            main_content_html=main_content,
            footer_text=f"Solicitud procesada para {company_name} ({industry})"
        )

        return {'subject': subject, 'html_body': html_body}

    @classmethod
    def generate_beta_approval_email(cls, lead_data: Dict[str, Any], temp_password: str, credits: int, magic_login_url: str = "", whatsapp_onboarding_url: str = "") -> Dict[str, str]:
        """
        Uses Krof AI logic to compose an approval email containing login credentials,
        granted credits, 1-click direct dashboard link, and WhatsApp onboarding link.
        """
        contact_name = lead_data.get('contact_name', 'Estimado/a')
        company_name = lead_data.get('company_name', 'su empresa')
        email = lead_data.get('email')
        industry = lead_data.get('industry', 'su rubro')

        subject = f"🎉 ¡Tu acceso Beta para {company_name} ha sido APROBADO!"

        direct_login_link = magic_login_url or "https://app.aikrofy.com/login"
        wa_link = whatsapp_onboarding_url or "https://wa.me/593988888888?text=Hola%20Krof%2C%20acabo%20de%20ser%20aprobado%20en%20el%20Beta%20de%20Aikrofy"

        main_content = f"""
        <p>Hola <strong>{contact_name}</strong>,</p>
        <p>Nos complace informarte que <strong>{company_name}</strong> ha sido seleccionada para acceder inmediatamente a la plataforma conversacional de <strong>Aikrofy</strong>.</p>
        
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 20px; margin: 24px 0; border-radius: 12px;">
            <p style="margin: 0 0 12px 0; font-weight: 700; color: #166534; font-size: 15px;">🔑 Credenciales de Acceso Privado:</p>
            <table border="0" cellpadding="4" cellspacing="0" width="100%" style="font-size: 14px; color: #15803d;">
                <tr>
                    <td width="140"><strong>Usuario/Email:</strong></td>
                    <td><code>{email}</code></td>
                </tr>
                <tr>
                    <td><strong>Contraseña Temporal:</strong></td>
                    <td><span style="background-color: #dcfce7; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-weight: 700; color: #14532d;">{temp_password}</span></td>
                </tr>
                <tr>
                    <td><strong>Créditos Asignados:</strong></td>
                    <td><strong>{credits} créditos iniciales</strong></td>
                </tr>
            </table>
        </div>
        
        <p style="font-size: 14px; color: #334155; margin-bottom: 20px;">Puedes comenzar tu configuración directamente en la Web o chatear de inmediato con <strong>Krof</strong> por WhatsApp para hacer tu Onboarding Mágico por notas de voz:</p>

        <div style="text-align: center; margin: 25px 0;">
            <a href="{direct_login_link}" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-weight: 700; font-size: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35); margin-bottom: 12px;">
                🚀 Entrar al Dashboard Web
            </a>
            <br>
            <a href="{wa_link}" style="background-color: #25D366; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 10px; font-weight: 700; font-size: 14px; display: inline-block; box-shadow: 0 4px 12px rgba(37, 211, 102, 0.35);">
                💬 Configurar por WhatsApp con Krof
            </a>
        </div>
        
        <p style="font-size: 13px; color: #64748b; text-align: center;">Recomendamos cambiar tu contraseña provisional luego de ingresar al panel de configuración.</p>
        """

        html_body = cls._build_html_template(
            header_title=f"¡Bienvenido a Aikrofy, {contact_name}!",
            badge_text="Acceso Aprobado",
            badge_color="#10b981",
            main_content_html=main_content,
            footer_text=f"Credenciales de acceso para {company_name} • Entorno Beta"
        )

        return {'subject': subject, 'html_body': html_body}

    @classmethod
    def generate_tenant_prospect_email(cls, company_name: str, prospect_name: str, goal: str, offer_details: str) -> Dict[str, str]:
        """
        AI Powered Copywriter for tenant companies sending personalized messages to their leads.
        """
        subject = f"Propuesta exclusiva de {company_name} para {prospect_name}"
        
        main_content = f"""
        <p>Hola <strong>{prospect_name}</strong>,</p>
        <p>Desde <strong>{company_name}</strong> queremos presentarte una propuesta especialmente adaptada a tus necesidades:</p>
        
        <div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 16px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; font-size: 15px; color: #1e293b;">{offer_details}</p>
        </div>
        
        <p>¿Te gustaría agendar una breve demostración o coordinar una llamada esta semana?</p>
        """

        html_body = cls._build_html_template(
            header_title=f"Mensaje de {company_name}",
            badge_text="Propuesta Especial",
            badge_color="#3b82f6",
            main_content_html=main_content,
            cta_text="Ver Detalles y Agendar",
            cta_url="https://app.aikrofy.com",
            footer_text=f"Enviado en representación de {company_name}"
        )

        return {'subject': subject, 'html_body': html_body}

    @classmethod
    def generate_employee_invitation_email(cls, company_name: str, employee_name: str, email: str, temp_password: str, role_title: str = "Administrador") -> Dict[str, str]:
        """
        Generates invitation email for newly provisioned team members/administrators.
        """
        subject = f"🔑 Has sido invitado como {role_title} en Aikrofy para {company_name}"

        login_url = "https://app.aikrofy.com/login"

        main_content = f"""
        <p>Hola <strong>{employee_name}</strong>,</p>
        <p>Se ha creado tu cuenta con rol de <strong>{role_title}</strong> para acceder al panel de control de <strong>{company_name}</strong> en la plataforma <strong>Aikrofy</strong>.</p>
        
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 20px; margin: 24px 0; border-radius: 12px;">
            <p style="margin: 0 0 12px 0; font-weight: 700; color: #166534; font-size: 15px;">🔑 Tus Credenciales de Acceso:</p>
            <table border="0" cellpadding="4" cellspacing="0" width="100%" style="font-size: 14px; color: #15803d;">
                <tr>
                    <td width="140"><strong>Usuario/Email:</strong></td>
                    <td><code>{email}</code></td>
                </tr>
                <tr>
                    <td><strong>Contraseña Temporal:</strong></td>
                    <td><span style="background-color: #dcfce7; padding: 3px 8px; border-radius: 4px; font-family: monospace; font-weight: 700; color: #14532d;">{temp_password}</span></td>
                </tr>
                <tr>
                    <td><strong>Empresa:</strong></td>
                    <td><strong>{company_name}</strong></td>
                </tr>
                <tr>
                    <td><strong>Rol Asignado:</strong></td>
                    <td><strong>{role_title}</strong></td>
                </tr>
            </table>
        </div>
        
        <p style="font-size: 14px; color: #334155; margin-bottom: 20px;">Puedes ingresar directamente al panel de administración haciendo clic en el siguiente botón:</p>

        <div style="text-align: center; margin: 25px 0;">
            <a href="{login_url}" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-weight: 700; font-size: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35);">
                🚀 Iniciar Sesión en Aikrofy
            </a>
        </div>
        
        <p style="font-size: 13px; color: #64748b; text-align: center;">Por motivos de seguridad, te sugerimos actualizar tu contraseña una vez que hayas ingresado a la plataforma.</p>
        """

        html_body = cls._build_html_template(
            header_title=f"Acceso de {role_title} — {company_name}",
            badge_text="Acceso Concedido",
            badge_color="#4f46e5",
            main_content_html=main_content,
            footer_text=f"Acceso Corporativo para {company_name} • Aikrofy"
        )

        return {'subject': subject, 'html_body': html_body}

