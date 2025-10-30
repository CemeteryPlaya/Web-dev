from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from myprofile.models import Extradition, TrackCode, Notification, Receipt


@login_required(login_url='login')
def extradition_view(request):
    
    """Оформление выдачи посылок пользователю (оператором).
    Можно выбрать трек-коды, указать пункт выдачи и комментарий.
    После оформления — треки получают статус 'claimed'."""
    

    if request.method == 'POST':
        track_codes_raw = request.POST.get('track_codes', '').strip()
        pickup_point = request.POST.get('pickup_point', '').strip()
        comment = request.POST.get('comment', '').strip()
        receipt_id = request.POST.get('receipt_id', '').strip()

        # Проверка заполненности
        if not track_codes_raw or not pickup_point:
            messages.error(request, "Введите трек-коды и пункт выдачи.")
            return redirect('extradition')

        # Разбиваем строки на список треков
        track_codes_list = [line.strip() for line in track_codes_raw.splitlines() if line.strip()]

        # Создаём выдачу
        extradition = Extradition.objects.create(
            user=request.user,
            issued_by=request.user,
            pickup_point=pickup_point,
            comment=comment,
            confirmed=True  # можно поменять на False, если подтверждение позже
        )

        # Привязка чека (если указан)
        if receipt_id:
            try:
                receipt = Receipt.objects.get(id=receipt_id)
                extradition.receipt = receipt
                extradition.save()
            except Receipt.DoesNotExist:
                messages.warning(request, f"Чек с ID {receipt_id} не найден.")

        # Обработка трек-кодов
        success, errors = 0, 0
        for code in track_codes_list:
            try:
                track = TrackCode.objects.get(track_code=code)
                extradition.track_codes.add(track)
                track.status = 'claimed'
                track.save()
                success += 1

                # Создать уведомление владельцу
                Notification.objects.create(
                    user=track.owner,
                    message=f"📦 Ваш трек {track.track_code} выдан в пункте: {pickup_point}"
                )

            except TrackCode.DoesNotExist:
                errors += 1
                messages.warning(request, f"❗ Трек-код '{code}' не найден.")

        messages.success(request, f"✅ Выдача оформлена ({success} треков, ошибок: {errors}).")
        return redirect('extradition')

    # GET-запрос — просто страница с формой
    return render(request, "extraditions.html", {
        'status_choices': TrackCode.STATUS_CHOICES
    })
