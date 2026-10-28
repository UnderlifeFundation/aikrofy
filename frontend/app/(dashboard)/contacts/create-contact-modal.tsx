'use client';

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { UserPlus, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import apiClient from '@/lib/api-client';

interface CreateContactModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateContactModal({ isOpen, onClose, onSuccess }: CreateContactModalProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');
  const [identNumber, setIdentNumber] = useState('');
  const [workCompany, setWorkCompany] = useState('');

  const resetForm = () => {
    setFirstName('');
    setLastName('');
    setEmail('');
    setPhone('');
    setCity('');
    setCountry('');
    setIdentNumber('');
    setWorkCompany('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstName.trim()) {
      toast.error(t('contacts.firstNameRequired', { defaultValue: 'El nombre es obligatorio' }));
      return;
    }

    try {
      setLoading(true);
      const payload = {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
        city: city.trim() || undefined,
        country: country.trim() || undefined,
        ident_number: identNumber.trim() || undefined,
        work_company: workCompany.trim() || undefined,
      };

      await apiClient.post('/customers', payload);
      toast.success(t('contacts.createSuccess', { defaultValue: 'Contacto creado correctamente' }));
      resetForm();
      onSuccess();
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.error || t('common.error', { defaultValue: 'Error al crear contacto' });
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-bold">
            <UserPlus className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            {t('contacts.newContactTitle', { defaultValue: 'Nuevo Contacto' })}
          </DialogTitle>
          <DialogDescription>
            {t('contacts.newContactDesc', { defaultValue: 'Ingresa los datos del nuevo lead o cliente para registrarlo en tu pipeline CRM.' })}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="firstName">{t('contacts.firstName', { defaultValue: 'Nombre *' })}</Label>
              <Input
                id="firstName"
                placeholder="Ej. Carlos"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="lastName">{t('contacts.lastName', { defaultValue: 'Apellido' })}</Label>
              <Input
                id="lastName"
                placeholder="Ej. Mendoza"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="phone">{t('contacts.phone', { defaultValue: 'Teléfono / WhatsApp' })}</Label>
              <Input
                id="phone"
                placeholder="Ej. +593991234567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">{t('contacts.email', { defaultValue: 'Correo Electrónico' })}</Label>
              <Input
                id="email"
                type="email"
                placeholder="Ej. carlos@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="city">{t('contacts.city', { defaultValue: 'Ciudad' })}</Label>
              <Input
                id="city"
                placeholder="Ej. Quito"
                value={city}
                onChange={(e) => setCity(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="country">{t('contacts.country', { defaultValue: 'País' })}</Label>
              <Input
                id="country"
                placeholder="Ej. Ecuador"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="workCompany">{t('contacts.workCompany', { defaultValue: 'Empresa / Organización' })}</Label>
              <Input
                id="workCompany"
                placeholder="Ej. Grupo Tech S.A."
                value={workCompany}
                onChange={(e) => setWorkCompany(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="identNumber">{t('contacts.identNumber', { defaultValue: 'Identificación (DNI/RUC)' })}</Label>
              <Input
                id="identNumber"
                placeholder="Ej. 1712345678"
                value={identNumber}
                onChange={(e) => setIdentNumber(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter className="pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              {t('common.cancel', { defaultValue: 'Cancelar' })}
            </Button>
            <Button type="submit" disabled={loading} className="bg-emerald-600 hover:bg-emerald-700 text-white">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common.saving', { defaultValue: 'Guardando...' })}
                </>
              ) : (
                t('common.save', { defaultValue: 'Guardar Contacto' })
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
