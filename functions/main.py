from firebase_admin import firestore, initialize_app, messaging
from firebase_functions import firestore_fn, https_fn, identity_fn, scheduler_fn
from firebase_functions.options import set_global_options

set_global_options(max_instances=10)
initialize_app()


def banner(title: str) -> None:
    line = "|" * 22
    print(f"\n{line}\n{title}\n{line}")


@https_fn.on_request()
def on_request_example(req: https_fn.Request) -> https_fn.Response:
    banner("Evento: on_request_example")
    return https_fn.Response("Arriba!")


@firestore_fn.on_document_created(document="usuarios/{userId}")
def on_user_created(event: firestore_fn.Event[firestore_fn.DocumentSnapshot | None]) -> None:
    banner("Evento: on_user_created")
    print(f"userId: {event.params['userId']}")
    print(f"data: {event.data.to_dict() if event.data else None}")


@identity_fn.before_user_created()
def create_user(event: identity_fn.AuthBlockingEvent) -> identity_fn.BeforeCreateResponse | None:
    banner("Evento: create_user")
    print(f"uid: {event.data.uid}, email: {event.data.email}")
    return None  # no bloquea la creación


@scheduler_fn.on_schedule(schedule="43 9 3 9 *", timezone="America/Guatemala")
def daily_scheduled_now(event: scheduler_fn.ScheduledEvent) -> None:
    banner("Evento: daily_scheduled_now")
    print("[daily_scheduled_now] Ejecución programada")


@firestore_fn.on_document_created(document="sales/{salesId}")
def on_sales_created(event: firestore_fn.Event[firestore_fn.DocumentSnapshot | None]) -> None:
    banner("Evento: on_sales_created")
    tag = "[on_sales_created]"
    sales_id = event.params["salesId"]

    if event.data is None:
        print(f"{tag} Sin datos en el evento ({sales_id})")
        return

    sale = event.data.to_dict() or {}
    date = sale.get("date")
    total = sale.get("total")
    user_id = sale.get("usuario")
    print(f"{tag} venta {sales_id}: date={date}, total={total}, usuario={user_id}")

    if not user_id:
        print(f"{tag} La venta no tiene campo 'usuario'")
        return

    try:
        user_doc = firestore.client().collection("usuarios").document(str(user_id)).get()
    except Exception as e:
        print(f"{tag} Error consultando usuarios/{user_id}: {e}")
        return

    if not user_doc.exists:
        print(f"{tag} El usuario {user_id} no existe")
        return

    tokens = (user_doc.to_dict() or {}).get("deviceTokens")
    if not isinstance(tokens, list):
        print(f"{tag} El usuario {user_id} no tiene 'deviceTokens' válido")
        return

    for token in tokens:
        if not token:
            continue
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title="SaleDetail",
                    body=f"Se registró una venta por un total de {total}",
                ),
                data={"salesId": sales_id, "date": str(date), "amount": str(total)},
                token=token,
            )
            response = messaging.send(message)
            print(f"{tag} Enviado a {token}: {response}")
        except Exception as e:
            print(f"{tag} Error enviando a {token}: {e}")
