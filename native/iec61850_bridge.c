#include "iec61850_client.h"
#include "mms_value.h"
#include "goose_receiver.h"
#include "goose_subscriber.h"
#include "hal_thread.h"
#include "tls_config.h"
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

static TLSConfiguration tls_config = NULL;
static volatile int running = 1;
static void stop_handler(int signal_id) { (void) signal_id; running = 0; }

static IedConnection connect_ied(const char* host, int port)
{
    IedClientError error;
    const char* ca = getenv("IEC61850_TLS_CA");
    const char* cert = getenv("IEC61850_TLS_CERT");
    const char* key = getenv("IEC61850_TLS_KEY");
    IedConnection con;
    if (ca && cert && key) {
        tls_config = TLSConfiguration_create();
        TLSConfiguration_setChainValidation(tls_config, true);
        TLSConfiguration_setAllowOnlyKnownCertificates(tls_config, true);
        if (!TLSConfiguration_setOwnKeyFromFile(tls_config, key, NULL) ||
            !TLSConfiguration_setOwnCertificateFromFile(tls_config, cert) ||
            !TLSConfiguration_addCACertificateFromFile(tls_config, ca)) {
            fprintf(stderr, "TLS-Zertifikat, Schlüssel oder CA konnte nicht geladen werden\n");
            return NULL;
        }
        con = IedConnection_createWithTlsSupport(tls_config);
    }
    else con = IedConnection_create();
    IedConnection_connect(con, &error, host, port);
    if (error != IED_ERROR_OK) {
        fprintf(stderr, "IEC61850-Verbindung fehlgeschlagen (Fehler %d)\n", error);
        IedConnection_destroy(con);
        return NULL;
    }
    return con;
}

static void report_callback(void* parameter, ClientReport report)
{
    LinkedList directory = (LinkedList) parameter;
    MmsValue* values = ClientReport_getDataSetValues(report);
    for (int i = 0; directory && i < LinkedList_size(directory); i++) {
        ReasonForInclusion reason = ClientReport_getReasonForInclusion(report, i);
        if (reason == IEC61850_REASON_NOT_INCLUDED) continue;
        LinkedList entry = LinkedList_get(directory, i);
        MmsValue* value = values ? MmsValue_getElement(values, i) : NULL;
        char buffer[2048] = "<kein Wert>";
        if (value) MmsValue_printToBuffer(value, buffer, sizeof(buffer));
        printf("REPORT\t%s\t%d\t%s\n", entry ? (char*) entry->data : "?", reason, buffer);
        fflush(stdout);
    }
}

static int monitor_report(IedConnection con, const char* rcb_ref, const char* data_set)
{
    IedClientError error;
    LinkedList directory = IedConnection_getDataSetDirectory(con, &error, data_set, NULL);
    if (!directory || error != IED_ERROR_OK) return error ? error : 1;
    ClientReportControlBlock rcb = IedConnection_getRCBValues(con, &error, rcb_ref, NULL);
    if (!rcb || error != IED_ERROR_OK) { LinkedList_destroy(directory); return error ? error : 1; }
    IedConnection_installReportHandler(con, rcb_ref, ClientReportControlBlock_getRptId(rcb), report_callback, directory);
    ClientReportControlBlock_setTrgOps(rcb, TRG_OPT_DATA_CHANGED | TRG_OPT_QUALITY_CHANGED | TRG_OPT_DATA_UPDATE | TRG_OPT_INTEGRITY | TRG_OPT_GI);
    ClientReportControlBlock_setRptEna(rcb, true);
    IedConnection_setRCBValues(con, &error, rcb, RCB_ELEMENT_TRG_OPS | RCB_ELEMENT_RPT_ENA, true);
    if (error == IED_ERROR_OK) {
        printf("STATUS\tReport-Abonnement aktiv\n"); fflush(stdout);
        while (running && IedConnection_getState(con) == IED_STATE_CONNECTED) Thread_sleep(100);
        ClientReportControlBlock_setRptEna(rcb, false);
        IedConnection_setRCBValues(con, &error, rcb, RCB_ELEMENT_RPT_ENA, true);
    }
    ClientReportControlBlock_destroy(rcb); LinkedList_destroy(directory);
    return error;
}

static void goose_callback(GooseSubscriber subscriber, void* parameter)
{
    (void) parameter; char buffer[4096];
    MmsValue_printToBuffer(GooseSubscriber_getDataSetValues(subscriber), buffer, sizeof(buffer));
    printf("GOOSE\t%s\t%u\t%u\t%s\t%s\n", GooseSubscriber_getGoCbRef(subscriber),
           GooseSubscriber_getStNum(subscriber), GooseSubscriber_getSqNum(subscriber),
           GooseSubscriber_isValid(subscriber) ? "gültig" : "ungültig", buffer); fflush(stdout);
}

static int monitor_goose(const char* interface_id)
{
    GooseReceiver receiver = GooseReceiver_create();
    GooseReceiver_setInterfaceId(receiver, interface_id);
    GooseSubscriber subscriber = GooseSubscriber_create("", NULL);
    GooseSubscriber_setObserver(subscriber); GooseSubscriber_setListener(subscriber, goose_callback, NULL);
    GooseReceiver_addSubscriber(receiver, subscriber); GooseReceiver_start(receiver);
    if (!GooseReceiver_isRunning(receiver)) { GooseReceiver_destroy(receiver); return 1; }
    printf("STATUS\tGOOSE-Mitschnitt aktiv\n"); fflush(stdout);
    while (running) Thread_sleep(100);
    GooseReceiver_stop(receiver); GooseReceiver_destroy(receiver); return 0;
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
    signal(SIGINT, stop_handler); signal(SIGTERM, stop_handler);
    if (argc >= 3 && strcmp(argv[1], "goose") == 0) return monitor_goose(argv[2]);
    if (argc < 4) { fprintf(stderr, "Aufruf: bridge <Aktion> <host> <port> ...\n"); return 2; }
    IedConnection con = connect_ied(argv[2], atoi(argv[3]));
    if (!con) return 3;
    int result = 0;
    IedClientError error = IED_ERROR_OK;
    if (strcmp(argv[1], "probe") == 0) printf("OK\n");
    else if (strcmp(argv[1], "browse") == 0) result = browse(con);
    else if (strcmp(argv[1], "report") == 0 && argc >= 6) result = monitor_report(con, argv[4], argv[5]);
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
    if (tls_config) TLSConfiguration_destroy(tls_config);
    return result == 0 ? 0 : 4;
}
