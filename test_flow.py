#!/usr/bin/env python3
"""
Script de teste do fluxo completo de agendamento.
Testa:
1. Registro de paciente
2. Registro de admin
3. Login do paciente
4. Login do admin
5. Verificação de navegação (patients vs admin)
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = 'http://localhost:8000/api'

def test_flow():
    print("=" * 60)
    print("TESTE DE FLUXO COMPLETO - SISTEMA DE AGENDAMENTOS")
    print("=" * 60)
    
    # 1. CRIAR PACIENTE
    print("\n1. Criando paciente...")
    patient_data = {
        'username': 'paciente_teste',
        'email': 'paciente@test.com',
        'password': 'senha123'
    }
    resp = requests.post(f'{BASE_URL}/users/', json=patient_data)
    if resp.status_code == 201:
        print(f"✓ Paciente criado com sucesso")
        patient = resp.json()
    else:
        print(f"✗ Erro ao criar paciente: {resp.status_code}")
        print(resp.text)
        return
    
    # 2. CRIAR ADMIN (PSICÓLOGA)
    print("\n2. Criando conta admin da psicóloga...")
    admin_data = {
        'username': 'psicologa_admin',
        'email': 'psicologa@example.com',
        'password': 'senha123'
    }
    resp = requests.post(f'{BASE_URL}/users/', json=admin_data)
    if resp.status_code == 201:
        print(f"✓ Admin criado com sucesso")
        admin = resp.json()
    else:
        print(f"✗ Erro ao criar admin: {resp.status_code}")
        print(resp.text)
        return
    
    # 3. LOGIN DO PACIENTE
    print("\n3. Paciente fazendo login...")
    login_data = {'username': 'paciente_teste', 'password': 'senha123'}
    resp = requests.post(f'{BASE_URL}/token-auth/', json=login_data)
    if resp.status_code == 200:
        patient_token = resp.json()['token']
        print(f"✓ Token do paciente obtido: {patient_token[:20]}...")
    else:
        print(f"✗ Erro no login do paciente: {resp.status_code}")
        return
    
    # 4. LOGIN DO ADMIN
    print("\n4. Psicóloga fazendo login...")
    login_data = {'username': 'psicologa_admin', 'password': 'senha123'}
    resp = requests.post(f'{BASE_URL}/token-auth/', json=login_data)
    if resp.status_code == 200:
        admin_token = resp.json()['token']
        print(f"✓ Token do admin obtido: {admin_token[:20]}...")
    else:
        print(f"✗ Erro no login do admin: {resp.status_code}")
        return
    
    # 5. PEGAR PERFIL DO PACIENTE
    print("\n5. Verificando perfil do paciente (deve ter is_staff=false)...")
    headers = {'Authorization': f'Token {patient_token}'}
    resp = requests.get(f'{BASE_URL}/users/profile/', headers=headers)
    if resp.status_code == 200:
        patient_profile = resp.json()
        is_staff = patient_profile.get('is_staff', False)
        print(f"✓ Perfil do paciente: is_staff={is_staff}")
        if not is_staff:
            print("  → Paciente será roteado para /calendar (tela de reserva)")
    else:
        print(f"✗ Erro ao pegar perfil do paciente: {resp.status_code}")
        return
    
    # 6. PEGAR PERFIL DO ADMIN
    print("\n6. Verificando perfil do admin (deve ter is_staff=true - MANUAL SETUP NEEDED)...")
    headers = {'Authorization': f'Token {admin_token}'}
    resp = requests.get(f'{BASE_URL}/users/profile/', headers=headers)
    if resp.status_code == 200:
        admin_profile = resp.json()
        is_staff = admin_profile.get('is_staff', False)
        print(f"✓ Perfil do admin: is_staff={is_staff}")
        if is_staff:
            print("  → Admin será roteado para /admin-dashboard")
        else:
            print("  ⚠ AVISO: is_staff=false. Execute comando para promover admin")
            print("    python manage.py shell")
            print("    >>> from django.contrib.auth import get_user_model")
            print("    >>> User = get_user_model()")
            print("    >>> user = User.objects.get(username='psicologa_admin')")
            print("    >>> user.is_staff = True")
            print("    >>> user.save()")
    else:
        print(f"✗ Erro ao pegar perfil do admin: {resp.status_code}")
        return
    
    # 7. PACIENTE BOOKING SLOTS
    print("\n7. Paciente consultando availability...")
    now = datetime.now()
    start = now.isoformat()
    end = (now + timedelta(days=7)).isoformat()
    headers = {'Authorization': f'Token {patient_token}'}
    resp = requests.get(f'{BASE_URL}/appointments/availabilities/?start={start}&end={end}', headers=headers)
    if resp.status_code == 200:
        slots = resp.json().get('available', [])
        print(f"✓ {len(slots)} slots disponíveis")
        if slots:
            first_slot = slots[0]
            print(f"  Primeiro slot: {first_slot}")
            
            # 8. PACIENTE RESERVAR SLOT
            print("\n8. Paciente reservando primeiro slot...")
            resp = requests.post(f'{BASE_URL}/appointments/', 
                               json={'scheduled_time': first_slot},
                               headers=headers)
            if resp.status_code == 201:
                appointment = resp.json()
                appt_id = appointment['id']
                print(f"✓ Agendamento criado: ID={appt_id}, Status={appointment['status']}")
            else:
                print(f"✗ Erro ao reservar: {resp.status_code}")
                print(resp.text)
                return
        else:
            print("  Nenhum slot disponível (isso não é erro, apenas sem horários)")
    else:
        print(f"✗ Erro ao consultar availability: {resp.status_code}")
        return
    
    # 9. ADMIN VÊ STATISTICAS
    print("\n9. Admin consultando estatísticas...")
    headers = {'Authorization': f'Token {admin_token}'}
    resp = requests.get(f'{BASE_URL}/appointments/statistics/', headers=headers)
    if resp.status_code == 200:
        stats = resp.json()
        print(f"✓ Estatísticas obtidas:")
        print(f"  - Pendentes: {stats.get('total_requested', 0)}")
        print(f"  - Confirmados: {stats.get('total_confirmed', 0)}")
        print(f"  - Cancelados: {stats.get('total_cancelled', 0)}")
        print(f"  - Hoje: {stats.get('today_appointments', 0)}")
    else:
        print(f"✗ Erro ao obter estatísticas: {resp.status_code}")
        print(resp.text)
        return
    
    # 10. ADMIN VÊ TODOS AGENDAMENTOS
    print("\n10. Admin listando todos os agendamentos...")
    resp = requests.get(f'{BASE_URL}/appointments/appointments/', headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        appointments = data if isinstance(data, list) else data.get('results', [])
        print(f"✓ Total de agendamentos: {len(appointments)}")
        for appt in appointments[:3]:  # Show first 3
            print(f"  - ID={appt['id']}, Paciente={appt['patient']}, Status={appt['status']}, Horário={appt['scheduled_time']}")
    else:
        print(f"✗ Erro ao listar agendamentos: {resp.status_code}")
        print(resp.text)
        return
    
    # 11. ADMIN CONFIRMA AGENDAMENTO
    if appointments:
        appt_to_confirm = appointments[0]
        appt_id = appt_to_confirm['id']
        if appt_to_confirm['status'] == 'requested':
            print(f"\n11. Admin confirmando agendamento ID={appt_id}...")
            resp = requests.post(f'{BASE_URL}/appointments/appointments/{appt_id}/confirm/', headers=headers)
            if resp.status_code == 200:
                print(f"✓ Agendamento confirmado com sucesso!")
            else:
                print(f"✗ Erro ao confirmar: {resp.status_code}")
                print(resp.text)
        else:
            print(f"\n11. Agendamento ID={appt_id} já está com status={appt_to_confirm['status']}")
    
    print("\n" + "=" * 60)
    print("TESTES CONCLUÍDOS COM SUCESSO!")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_flow()
    except Exception as e:
        print(f"\n✗ Erro: {e}")
        import traceback
        traceback.print_exc()
