"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Send, User, Mail, MessageSquare, Loader2, Info } from "lucide-react";

interface Company {
  id: number;
  name: string;
  agent_name: string;
  public_slug: string;
  logo_url: string | null;
}

export default function ConversationalLandingPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [hasAccess, setHasAccess] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  const [messages, setMessages] = useState<{role: 'user'|'agent', content: string}[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Use the API URL from env, default to same origin if not set
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api";

  useEffect(() => {
    const fetchCompany = async () => {
      try {
        const res = await fetch(`${apiUrl}/companies/public/${slug}`);
        if (!res.ok) throw new Error("Company not found");
        const json = await res.json();
        setCompany(json.data);
      } catch (err) {
        setError("Lo sentimos, no encontramos esta página.");
      } finally {
        setLoading(false);
      }
    };
    fetchCompany();
  }, [slug, apiUrl]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleGatekeeperSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.trim()) return;
    setHasAccess(true);
    setMessages([
      { role: "agent", content: `¡Hola ${name}! Soy ${company?.agent_name}, asistente de ${company?.name}. ¿En qué te puedo ayudar hoy?` }
    ]);
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !company) return;

    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsTyping(true);

    try {
      // Create a unique session ID based on email
      const sessionId = `webchat_${company.id}_${email.replace(/[^a-zA-Z0-9]/g, "")}`;
      
      const res = await fetch(`${apiUrl}/webhooks/webchat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_id: company.id,
          session_id: sessionId,
          message: userMessage,
          contact_name: name,
          contact_email: email
        })
      });
      
      if (!res.ok) throw new Error("API Error");
      const data = await res.json();
      
      setMessages(prev => [...prev, { role: "agent", content: data.message || "Lo siento, hubo un error." }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "agent", content: "Lo siento, mi conexión ha fallado temporalmente." }]);
    } finally {
      setIsTyping(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-emerald-500 animate-spin" />
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">
        <div className="text-center p-8 glass-panel rounded-2xl">
          <Info className="w-12 h-12 text-rose-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold">{error}</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 flex flex-col font-sans overflow-hidden">
      {/* Dynamic Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-emerald-500/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-500/20 rounded-full blur-[120px]" />
      </div>

      <AnimatePresence mode="wait">
        {!hasAccess ? (
          <motion.div
            key="gatekeeper"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="flex-1 flex items-center justify-center p-4 relative z-10"
          >
            <div className="w-full max-w-md bg-white/5 backdrop-blur-xl border border-white/10 p-8 rounded-3xl shadow-2xl">
              <div className="text-center mb-8">
                {company.logo_url ? (
                  <img src={company.logo_url} alt={company.name} className="w-20 h-20 mx-auto rounded-2xl mb-4 object-cover" />
                ) : (
                  <div className="w-20 h-20 mx-auto bg-gradient-to-tr from-emerald-400 to-cyan-500 rounded-2xl mb-4 flex items-center justify-center shadow-lg">
                    <MessageSquare className="w-10 h-10 text-white" />
                  </div>
                )}
                <h1 className="text-3xl font-bold text-white tracking-tight">{company.name}</h1>
                <p className="text-slate-400 mt-2">Inicia una conversación directa con nuestro asistente inteligente.</p>
              </div>

              <form onSubmit={handleGatekeeperSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Tu Nombre</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-slate-500" />
                    </div>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="block w-full pl-10 pr-3 py-3 border border-white/10 rounded-xl leading-5 bg-black/20 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all sm:text-sm"
                      placeholder="Ej. Juan Pérez"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Tu Correo Electrónico</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Mail className="h-5 w-5 text-slate-500" />
                    </div>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="block w-full pl-10 pr-3 py-3 border border-white/10 rounded-xl leading-5 bg-black/20 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all sm:text-sm"
                      placeholder="Ej. juan@correo.com"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-semibold text-white bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-all transform hover:scale-[1.02] active:scale-95"
                >
                  Comenzar Chat
                </button>
              </form>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="chat"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="flex-1 flex flex-col h-full max-w-4xl mx-auto w-full p-0 sm:p-6 relative z-10 justify-end sm:justify-center"
          >
            <div className="h-[75dvh] max-h-[75dvh] sm:h-full sm:max-h-none bg-white/5 backdrop-blur-xl border border-white/10 rounded-tl-3xl rounded-tr-none sm:rounded-3xl shadow-2xl flex flex-col overflow-hidden">
              {/* Header */}
              <div className="px-6 py-4 border-b border-white/10 bg-black/20 flex items-center">
                {company.logo_url ? (
                  <img src={company.logo_url} alt="Logo" className="w-10 h-10 rounded-full mr-3 object-cover" />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-400 to-cyan-500 mr-3 flex items-center justify-center">
                    <MessageSquare className="w-5 h-5 text-white" />
                  </div>
                )}
                <div>
                  <h2 className="text-lg font-bold text-white leading-tight">{company.agent_name}</h2>
                  <p className="text-xs text-emerald-400 font-medium flex items-center">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 mr-1 animate-pulse" /> En línea
                  </p>
                </div>
              </div>

              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                      msg.role === 'user' 
                        ? 'bg-gradient-to-br from-emerald-500 to-emerald-600 text-white rounded-tr-sm shadow-emerald-900/20' 
                        : 'bg-white/10 border border-white/5 text-slate-100 rounded-tl-sm backdrop-blur-sm shadow-black/20'
                    } shadow-lg`}
                    >
                      <p className="text-[15px] whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                    </div>
                  </motion.div>
                ))}
                
                {isTyping && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                    <div className="bg-white/10 border border-white/5 rounded-2xl rounded-tl-sm px-5 py-4 backdrop-blur-sm flex items-center space-x-2">
                      <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </motion.div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-4 bg-black/20 border-t border-white/10">
                <form onSubmit={sendMessage} className="relative flex items-center">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Escribe tu mensaje aquí..."
                    disabled={isTyping}
                    className="w-full pl-5 pr-14 py-4 bg-white/5 border border-white/10 rounded-full text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:bg-white/10 transition-all disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || isTyping}
                    className="absolute right-2 p-2 bg-emerald-500 hover:bg-emerald-400 text-white rounded-full transition-all disabled:opacity-50 disabled:hover:bg-emerald-500"
                  >
                    <Send className="w-5 h-5 ml-[2px]" />
                  </button>
                </form>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
