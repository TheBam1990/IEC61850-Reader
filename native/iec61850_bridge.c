#include "iec61850_client.h"
#include "mms_value.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

static IedConnection connect_ied(const char* host, int port)
{
    IedClientError error;
    IedConnection con = IedConnection_create();
    IedConnection_connect(con, &error, host, port);
    if (error != IED_ERROR_OK) {
        fprintf(stderr, "IEC61850-Verbindung fehlgeschlagen (Fehler %d)\n", error);
        IedConnection_destroy(con);
        return NULL;
    }
    return con;
}

static void print_data_directory(IedConnection con, const char* ref, int depth)
{
    if (depth > 12) return;
    IedClientError error;
    LinkedList list = IedConnection_getDataDirectory(con, &error, ref);
    if (list == NULL || error != IED_ERROR_OK) return;
    LinkedList item = LinkedList_getNext(list);
    while (item) {
        const char* name = (const char*) item->data;
        char child[1024];
        snprintf(child, sizeof(child), "%s.%s", ref, name);
        printf("DA\t%s\n", child);
        print_data_directory(con, child, depth + 1);
        item = LinkedList_getNext(item);
    }
    LinkedList_destroy(list);
}

static int browse(IedConnection con)
{
    IedClientError error;
    LinkedList devices = IedConnection_getLogicalDeviceList(con, &error);
    if (error != IED_ERROR_OK || devices == NULL) return error ? error : 1;
    for (LinkedList device = LinkedList_getNext(devices); device; device = LinkedList_getNext(device)) {
        const char* ld = (const char*) device->data;
        printf("LD\t%s\n", ld);
        LinkedList nodes = IedConnection_getLogicalDeviceDirectory(con, &error, ld);
        for (LinkedList node = LinkedList_getNext(nodes); node; node = LinkedList_getNext(node)) {
            const char* ln = (const char*) node->data;
            char ln_ref[512];
            snprintf(ln_ref, sizeof(ln_ref), "%s/%s", ld, ln);
            printf("LN\t%s\n", ln_ref);
            LinkedList objects = IedConnection_getLogicalNodeDirectory(con, &error, ln_ref, ACSI_CLASS_DATA_OBJECT);
            for (LinkedList object = LinkedList_getNext(objects); object; object = LinkedList_getNext(object)) {
                char do_ref[768];
                snprintf(do_ref, sizeof(do_ref), "%s.%s", ln_ref, (char*) object->data);
                printf("DO\t%s\n", do_ref);
                print_data_directory(con, do_ref, 0);
            }
            LinkedList_destroy(objects);
            LinkedList urcbs = IedConnection_getLogicalNodeDirectory(con, &error, ln_ref, ACSI_CLASS_URCB);
            for (LinkedList x = LinkedList_getNext(urcbs); x; x = LinkedList_getNext(x)) printf("URCB\t%s.%s\n", ln_ref, (char*) x->data);
            LinkedList_destroy(urcbs);
            LinkedList brcbs = IedConnection_getLogicalNodeDirectory(con, &error, ln_ref, ACSI_CLASS_BRCB);
            for (LinkedList x = LinkedList_getNext(brcbs); x; x = LinkedList_getNext(x)) printf("BRCB\t%s.%s\n", ln_ref, (char*) x->data);
            LinkedList_destroy(brcbs);
        }
        LinkedList_destroy(nodes);
    }
    LinkedList_destroy(devices);
    return 0;
}

static MmsValue* make_value(const char* type, const char* text)
{
    if (strcmp(type, "bool") == 0) return MmsValue_newBoolean(strcmp(text, "0") != 0 && strcmp(text, "false") != 0);
    if (strcmp(type, "int") == 0) return MmsValue_newIntegerFromInt32((int32_t) strtol(text, NULL, 0));
    if (strcmp(type, "uint") == 0) return MmsValue_newUnsignedFromUint32((uint32_t) strtoul(text, NULL, 0));
    if (strcmp(type, "float") == 0) return MmsValue_newFloat((float) strtod(text, NULL));
    if (strcmp(type, "string") == 0) return MmsValue_newVisibleString(text);
    return NULL;
}

int main(int argc, char** argv)
{
    if (argc < 4) { fprintf(stderr, "Aufruf: bridge <probe|browse|read|write|control> <host> <port> ...\n"); return 2; }
    IedConnection con = connect_ied(argv[2], atoi(argv[3]));
    if (!con) return 3;
    int result = 0;
    IedClientError error = IED_ERROR_OK;
    if (strcmp(argv[1], "probe") == 0) printf("OK\n");
    else if (strcmp(argv[1], "browse") == 0) result = browse(con);
    else if (strcmp(argv[1], "read") == 0 && argc >= 6) {
        FunctionalConstraint fc = FunctionalConstraint_fromString(argv[5]);
        MmsValue* value = IedConnection_readObject(con, &error, argv[4], fc);
        if (error == IED_ERROR_OK && value) {
            char buffer[4096]; MmsValue_printToBuffer(value, buffer, sizeof(buffer)); printf("VALUE\t%s\n", buffer); MmsValue_delete(value);
        } else result = error ? error : 1;
    }
    else if (strcmp(argv[1], "write") == 0 && argc >= 8) {
        MmsValue* value = make_value(argv[6], argv[7]);
        if (!value) result = 2;
        else { IedConnection_writeObject(con, &error, argv[4], FunctionalConstraint_fromString(argv[5]), value); result = error; MmsValue_delete(value); }
    }
    else if (strcmp(argv[1], "control") == 0 && argc >= 12) {
        ControlObjectClient control = ControlObjectClient_create(argv[4], con);
        MmsValue* value = make_value(argv[5], argv[6]);
        if (!control || !value) result = 2;
        else {
            ControlObjectClient_setOrigin(control, NULL, atoi(argv[8]));
            ControlObjectClient_setTestMode(control, atoi(argv[9]) != 0);
            ControlObjectClient_setInterlockCheck(control, atoi(argv[10]) != 0);
            ControlObjectClient_setSynchroCheck(control, atoi(argv[11]) != 0);
            if (strcmp(argv[7], "select") == 0) result = ControlObjectClient_selectWithValue(control, value) ? 0 : 1;
            else if (strcmp(argv[7], "cancel") == 0) result = ControlObjectClient_cancel(control) ? 0 : 1;
            else result = ControlObjectClient_operate(control, value, 0) ? 0 : 1;
        }
        if (value) MmsValue_delete(value);
        if (control) ControlObjectClient_destroy(control);
    }
    else result = 2;
    if (result != 0) fprintf(stderr, "IEC61850-Aktion fehlgeschlagen (Fehler %d)\n", result);
    IedConnection_close(con); IedConnection_destroy(con);
    return result == 0 ? 0 : 4;
}
