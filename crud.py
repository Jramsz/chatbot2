import os

from bson import ObjectId
from pymongo import MongoClient

# Ejemplo: export MONGO_URI='mongodb://usuario:clave@localhost:27017/?authSource=admin'
client = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017/'))
db = client['Practica']
collection = db['Usuarios']


def crear(nombre, edad):
    result = collection.insert_one({"nombre": nombre, "edad": edad})
    return result.inserted_id


def listar():
    return list(collection.find())


def buscar_por_nombre(nombre):
    return list(collection.find({"nombre": {"$regex": nombre, "$options": "i"}}))


def actualizar(id_documento, nombre=None, edad=None):
    cambios = {}
    if nombre:
        cambios["nombre"] = nombre
    if edad:
        cambios["edad"] = edad
    if not cambios:
        return 0
    result = collection.update_one({"_id": ObjectId(id_documento)}, {"$set": cambios})
    return result.modified_count


def eliminar(id_documento):
    result = collection.delete_one({"_id": ObjectId(id_documento)})
    return result.deleted_count


def mostrar(docs):
    if not docs:
        print("Sin resultados.")
    for doc in docs:
        print(f"ID: {doc['_id']} | Nombre: {doc['nombre']} | Edad: {doc['edad']}")


def menu():
    while True:
        print("\n--- CRUD MongoDB ---")
        print("1. Crear\n2. Listar\n3. Buscar por nombre\n4. Actualizar\n5. Eliminar\n0. Salir")
        opcion = input("Opcion: ").strip()

        try:
            if opcion == "1":
                print("Insertado con ID:", crear(input("Nombre: "), input("Edad: ")))
            elif opcion == "2":
                mostrar(listar())
            elif opcion == "3":
                mostrar(buscar_por_nombre(input("Nombre a buscar: ")))
            elif opcion == "4":
                id_doc = input("ID del documento: ")
                n = actualizar(id_doc, input("Nuevo nombre (vacio = sin cambio): "),
                               input("Nueva edad (vacio = sin cambio): "))
                print(f"Documentos modificados: {n}")
            elif opcion == "5":
                n = eliminar(input("ID del documento: "))
                print(f"Documentos eliminados: {n}")
            elif opcion == "0":
                break
            else:
                print("Opcion no valida.")
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    menu()
