from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models import F
from myprofile.models import ExtraditionReceipt, Receipt, ReceiptItem, TrackCode, Notification


@login_required(login_url='login')
def extradition_receipt_view(request):
    """
    Оформление выдачи по чеку:
    Показывает только оплаченные чеки, у которых ВСЕ трек-коды имеют статус 'ready'.
    """
    if request.method == 'POST':
        receipt_id = request.POST.get('receipt_id')
        pickup_point = request.POST.get('pickup_point', '').strip()
        comment = request.POST.get('comment', '').strip()

        if not receipt_id or not pickup_point:
            messages.error(request, "⚠️ Укажите чек и пункт выдачи.")
            return redirect('extradition_receipt')

        try:
            receipt = Receipt.objects.get(id=receipt_id)
        except Receipt.DoesNotExist:
            messages.error(request, "❌ Чек не найден.")
            return redirect('extradition_receipt')

        # Проверяем, не выдан ли уже этот чек
        if hasattr(receipt, 'extradition_receipt'):
            messages.warning(request, f"❗ Чек #{receipt.id} уже выдан ранее.")
            return redirect('extradition_receipt')

        # Проверяем, все ли треки имеют статус 'ready'
        items = ReceiptItem.objects.filter(receipt=receipt)
        if not items.exists():
            messages.error(request, f"❌ У чека #{receipt.id} нет трек-кодов.")
            return redirect('extradition_receipt')

        not_ready = items.exclude(track_code__status='ready').count()
        if not_ready > 0:
            messages.warning(request, f"⚠️ У чека #{receipt.id} есть трек-коды, не готовые к выдаче.")
            return redirect('extradition_receipt')

        # Создаём запись о выдаче
        extradition = ExtraditionReceipt.objects.create(
            receipt=receipt,
            issued_by=request.user,
            pickup_point=pickup_point,
            comment=comment
        )

        # Обновляем статусы треков → 'claimed'
        for item in items:
            track = item.track_code
            track.status = 'claimed'
            track.save()

            # Создаём уведомление владельцу
            Notification.objects.create(
                user=track.owner,
                message=f"📦 Трек {track.track_code} выдан в пункте: {pickup_point}"
            )

        messages.success(request, f"✅ Чек #{receipt.id} успешно выдан ({items.count()} треков).")
        return redirect('extradition_receipt')

    # ---- GET-запрос: выбираем доступные чеки ----
    # Только оплаченные, невыданные, и все трек-коды = ready
    available_receipts = (
        Receipt.objects.filter(is_paid=True, extradition_receipt__isnull=True)
        .annotate(
            total_tracks=Count('items'),
            ready_tracks=Count('items', filter=Q(items__track_code__status='ready'))
        )
        .filter(total_tracks=F('ready_tracks'))  # все треки готовы
    )

    extraditions = ExtraditionReceipt.objects.select_related('receipt', 'issued_by')

    return render(request, 'extradition_receipt.html', {
        'receipts': available_receipts,
        'extraditions': extraditions
    })
